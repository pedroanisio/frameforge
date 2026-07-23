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


# The ONE sanctioned engine text fallback (ADR-0006, GH #74). Every text
# surface — flow AND absolute objects — defaults to the document's reserved
# `body` style; only a document without one gets this constant.
_SANCTIONED = {"family": "serif", "family_primary": "serif", "size": 12.0,
               "lh": 1.4, "color": "#1c1c1c", "align": "left"}

# The reserved `tokens.styles` names the engine consumes (ADR-0006) — THE
# single source of truth. The spec (§5.2.2), the MCP guide, and
# `describe_capabilities("style")` must name exactly these keys, and every
# reserved-style literal in the renderer must appear here
# (tests/test_reserved_styles_sync.py enforces both directions). An authored
# reserved style wins wholesale; absence falls back to the documented default.
RESERVED_STYLES = {
    "body": "the flow renderer's DEFAULT text style — define it (in "
            "tokens.styles) to set the document face/size/colour; it cascades "
            "to every text surface (GH #74). Absent → the single sanctioned "
            "engine fallback (ADR-0006).",
    "caption": "styles generated figure and table captions (fallback: bold "
               "for table captions; italic + centered for figure captions).",
    "code": "styles code blocks (fallback: monospace / 10 / #333).",
    "toc": "styles generated table-of-contents entry lines (fallback: "
           "base + lh 1.5).",
    "toc_title": "styles the generated table-of-contents title (fallback: "
                 "entry size × 1.5, bold).",
}


# The CSS-inherited text properties an inline run takes from its parent when it
# does not declare them (`resolve(ref, base=...)`).
#
# DELIBERATELY EXCLUDED — metric-affecting properties. The text fitter measures a
# line ONCE, from the object's base style, with a per-character `avg` estimate
# that models none of these. A run is already inside its parent `<text>`/`<div>`,
# so it INHERITS them through CSS anyway; re-emitting them per run adds nothing
# visually but would let a future divergence widen a run past the width that was
# measured for it. Keep them out: letter_spacing, word_spacing, font_stretch,
# font_variant*, font_feature_settings, font_variation_settings, text_transform,
# tab_size, hyphens, hanging_punctuation, hyphenate_*.
#
# Also excluded: box/fit properties (overflow, min_font_size, text_overflow,
# max_lines, valign, nowrap, css) — they belong to the box, not to a run inside
# it — and `text_decoration`, which CSS does not inherit.
#
# `family`, `size`, `weight`, `italic`, `color`, `align` and `lh` inherit through
# the per-key default `d` inside `resolve`, so they are not repeated here.
INHERITED_TEXT_PROPERTIES = (
    "white_space", "word_break", "overflow_wrap",
    "text_align_last", "text_indent", "writing_mode", "direction",
    "unicode_bidi", "text_shadow",
)


class TextStyleResolver:
    def __init__(self, text_styles, styles, color_resolver):
        self.text_styles = text_styles or {}
        self.styles = styles or {}
        self._color = color_resolver
        # Two-phase: resolve `body` against the sanctioned constant, then use
        # the result as the per-key default for every later resolve — so the
        # document's body style cascades to all text (GH #74; was a second,
        # divergent sans/14/1.25 trio private to this resolver).
        self._default = dict(_SANCTIONED)
        if "body" in self.text_styles or "body" in self.styles:
            body = self.resolve("body")
            self._default = {k: body[k] for k in _SANCTIONED}

    def resolve(self, ref, base=None):
        """Resolve a style ref; with `base`, inherit what the ref does not declare.

        `base` is an already-resolved style dict standing in as the per-key
        default — the CSS inheritance model, used for the inline runs of a
        `text.spans` list. Without it, resolution falls back to the document's
        `body` style exactly as before, so every existing call is unchanged.

        A run that declares only `{"color": ...}` must keep its parent object's
        family, size and weight: resolving such a run against the DOCUMENT
        default instead re-materialised `font-family` from `tokens.styles.body`,
        so per-run syntax colours inside a monospaced block silently redrew every
        coloured run in the UI sans face (GH P1-1).
        """
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
        # Per-key defaults: the inherited base when there is one, else the
        # document's `body` style (the pre-existing behaviour).
        d = base if base is not None else self._default
        fam = merged.get("font_family") or merged.get("font")
        if fam is None:
            family = d["family"]
            family_primary = d["family_primary"]
        else:
            # Preserve the WHOLE fallback stack so the SVG stays portable when the
            # primary face isn't installed in the viewer (else a bare "font-family:Inter"
            # falls back to the UA default serif). Role strings ("sans"/"serif"/"mono")
            # already map to a terminating generic, so single-role styles are unchanged.
            fam_list = [str(x) for x in (fam if isinstance(fam, list) else [fam]) if x]
            families = [FONT_MAP.get(x, x) for x in fam_list] or [d["family"]]
            if families[-1] not in ("sans-serif", "serif", "monospace"):
                families.append("sans-serif")
            family = ", ".join(families)
            family_primary = families[0]
        size = (num(merged.get("font_size") or merged.get("size"), d["size"])
                or d["size"])
        weight = merged.get("font_weight") or merged.get("weight")
        if weight is None and merged.get("bold"):
            weight = 700
        if weight is None:
            # Inherited when a base is in play; "normal" is the document default.
            weight = d.get("weight", "normal")
        bold = str(weight) in ("bold", "600", "700", "800", "900") or (isinstance(weight, int) and weight >= 600)
        # line-height: a ratio (<=4) or an absolute length ("68px") → ratio
        lhv = merged.get("line_height")
        if isinstance(lhv, str):
            n = num(lhv)
            lh = (n / size) if (n and size) else self._default["lh"]
        elif isinstance(lhv, (int, float)) and not isinstance(lhv, bool):
            lh = lhv if lhv <= 4 else lhv / size
        else:
            lh = d["lh"]
        # per-char advance estimate (no real shaping available) — used for fit + the check
        avg = 0.60 if "mono" in family else 0.52
        if bold:
            avg *= 1.04
        tw = merged.get("text_wrap")
        if "italic" in merged or "font_style" in merged:
            italic = bool(merged.get("italic")) or merged.get("font_style") == "italic"
        else:
            italic = bool(d.get("italic", False))
        out = {
            "family": family, "family_primary": family_primary,
            "size": size, "weight": weight, "bold": bold,
            "italic": italic,
            "color": self._color.resolve(merged.get("color")) or d["color"],
            "align": merged.get("text_align") or merged.get("align") or d["align"],
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
        if base is not None:
            for key in INHERITED_TEXT_PROPERTIES:
                if key not in merged and out.get(key) is None:
                    out[key] = base.get(key)
        return out

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
