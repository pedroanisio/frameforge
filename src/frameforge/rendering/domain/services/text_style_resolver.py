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

from frameforge.rendering.domain.geometry import num

# Generic-family map (FrameForge font roles → browser generic families).
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
        # Preserve the WHOLE fallback stack so the SVG stays portable when the
        # primary face isn't installed in the viewer (else a bare "font-family:Inter"
        # falls back to the UA default serif). Role strings ("sans"/"serif"/"mono")
        # already map to a terminating generic, so single-role styles are unchanged.
        fam_list = [str(x) for x in (fam if isinstance(fam, list) else [fam]) if x] or ["sans"]
        families = [FONT_MAP.get(x, x) for x in fam_list]
        if families[-1] not in ("sans-serif", "serif", "monospace"):
            families.append("sans-serif")
        family = ", ".join(families)
        family_primary = families[0]
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
            "family": family, "family_primary": family_primary,
            "size": size, "weight": weight, "bold": bold,
            "italic": bool(merged.get("italic")) or merged.get("font_style") == "italic",
            "color": self._color.resolve(merged.get("color")) or "#1c1c1c",
            "align": merged.get("text_align") or merged.get("align") or "left",
            "lh": lh, "avg": avg,
            # ---- directly renderable CSS text surface ----
            "letter_spacing": self._css_length(merged.get("letter_spacing")),
            "word_spacing": self._css_length(merged.get("word_spacing")),
            "text_decoration": self._text_decoration(merged.get("text_decoration")),
            "text_transform": merged.get("text_transform"),
            "text_shadow": self._text_shadow(merged.get("text_shadow")),
            "white_space": merged.get("white_space"),
            "word_break": merged.get("word_break"),
            "overflow_wrap": merged.get("overflow_wrap"),
            "hyphens": merged.get("hyphens"),
            "font_variant": merged.get("font_variant"),
            "font_variant_caps": merged.get("font_variant_caps"),
            "font_variant_numeric": merged.get("font_variant_numeric"),
            "font_variant_ligatures": merged.get("font_variant_ligatures"),
            "font_feature_settings": merged.get("font_feature_settings"),
            "font_variation_settings": merged.get("font_variation_settings"),
            "font_kerning": merged.get("font_kerning"),
            "font_stretch": merged.get("font_stretch"),
            "text_align_last": merged.get("text_align_last"),
            "text_indent": self._css_length(merged.get("text_indent")),
            "hanging_punctuation": merged.get("hanging_punctuation"),
            "hyphenate_character": merged.get("hyphenate_character"),
            "hyphenate_limit_chars": self._hyphenate_limit_chars(merged.get("hyphenate_limit_chars")),
            "tab_size": self._css_length(merged.get("tab_size")),
            "writing_mode": merged.get("writing_mode"),
            "direction": merged.get("direction"),
            "unicode_bidi": merged.get("unicode_bidi"),
            "css": merged.get("css"),
            # ---- text-fit contract surface ----
            "overflow": merged.get("overflow"),
            "min_font_size": num(merged.get("min_font_size")),
            "text_overflow": merged.get("text_overflow"),
            "max_lines": merged.get("line_clamp") or merged.get("max_lines"),
            "valign": merged.get("vertical_align") or merged.get("v_align"),
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

    @staticmethod
    def _hyphenate_limit_chars(value):
        if not isinstance(value, list) or len(value) != 3:
            return None
        if not all(isinstance(v, int) and not isinstance(v, bool) for v in value):
            return None
        return " ".join(str(v) for v in value)

    def _text_shadow(self, value):
        if value is None or value == "none":
            return None
        items = value if isinstance(value, list) else [value]
        shadows = []
        for item in items:
            if isinstance(item, str):
                shadows.append(item)
                continue
            if not isinstance(item, dict):
                continue
            x = self._css_length(item.get("offset_x", item.get("x", 0)))
            y = self._css_length(item.get("offset_y", item.get("y", 0)))
            blur = self._css_length(item.get("blur", 0))
            color = self._color.resolve(item.get("color")) or item.get("color")
            parts = [x, y, blur]
            if color:
                parts.append(str(color))
            shadows.append(" ".join(str(p) for p in parts if p is not None))
        return ", ".join(shadows) if shadows else None
