"""HtmlPainter — the HTML backend as a `ScenePainter`, not a second renderer.

Why this exists
---------------
The HTML output used to be a standalone 1462-line transform implementing the
coarse `DocumentRenderer` port: it received the raw document and re-derived
everything the shared builder already does — group layout, text fitting and
wrapping, tables, UML, connectors, dimensions. The result was structural
duplication with a measurable cost: it drew 13 of the model's 34 object types
and emitted the other 21 as labelled "unsupported type" placeholders, and every
engine improvement had to be hand-copied to reach HTML at all.

This painter deletes that duplication. It drives the *same* `Renderer` builder as
SVG and TikZ, so layout, typography, tables, UML and connectors arrive already
solved. What is left for a backend to decide is how a resolved mark becomes
markup — and for the vector marks, HTML's own answer is inline SVG, which is
exactly what `SvgPainter` already emits correctly.

So the geometry is inherited rather than reimplemented (DRY), and this class
overrides only what HTML does *differently*: the structural seams that carry the
layer tree and object identity into the DOM, and the typography seam that hoists
a named text style into a reusable CSS class. Subclassing is the honest
relationship here — an `HtmlPainter` genuinely *is* an SVG-emitting painter plus
a semantic shell, and it is substitutable for one everywhere (LSP): pass it to
the builder and every primitive still renders.

What HTML adds over the SVG backend
-----------------------------------
* `<g class="fg-layer" data-layer=… data-z=…>` — the authored layer tree, which
  the flat SVG display list discards.
* `<g id=… class="fg-obj fg-<type>">` — the authored object identity, so a
  consumer can address `#hero` or style every `.fg-rect`.
* `class="fg-ts-<name>"` on text carrying a named style, plus the collected
  declarations for a hoisted stylesheet.
* the palette as `:root` custom properties (`--fg-navy`), collected here and
  emitted by the document adapter.

Known boundary — paint literals
-------------------------------
Geometry paint is emitted as the resolved literal (`fill="#14213f"`), exactly as
the SVG backend does, NOT as `fill="var(--fg-navy)"`. CSS custom properties are
reliable inside a `style` attribute but are not dependable inside an SVG
*presentation* attribute across consumers, and a paint that silently fails to
resolve is a blank shape. The palette is therefore published as `:root`
variables for theming and authoring use, while the marks stay literal and
render identically in every consumer. Text paint, which already travels in a
`style` attribute, is not affected by this limitation. This is a deliberate
correctness trade, and it is the one place HTML output is less "tokenised" than
the authored document.
"""
from __future__ import annotations

import re

from frameforge.rendering.domain.geometry import esc
from frameforge.rendering.domain.services.a11y import derive_semantics
from frameforge.rendering.infrastructure.painters.svg import SvgPainter

#: A CSS identifier is [A-Za-z0-9-_]; anything else in a token name is folded to
#: `-` so an authored token like "brand blue/2" still yields a usable class.
_NON_IDENT = re.compile(r"[^A-Za-z0-9_-]+")


def css_ident(name) -> str:
    """Fold an authored token name into a safe CSS identifier fragment."""
    ident = _NON_IDENT.sub("-", str(name)).strip("-")
    if ident and ident[0].isdigit():
        ident = f"n{ident}"           # a CSS ident may not start with a digit
    return ident or "unnamed"


class HtmlPainter(SvgPainter):
    """A `ScenePainter` whose medium is an HTML document with inline SVG marks."""

    #: HTML embeds real SVG, so the `<filter>` chains the builder composites are
    #: rendered for real — same capability as the SVG backend.
    supports_filters = True

    def __init__(self, color_resolver, warn=None):
        super().__init__(color_resolver, warn)
        # Collected across every page so the document adapter can hoist one
        # stylesheet. Insertion-ordered: the emitted CSS is deterministic.
        self.text_styles: dict[str, dict] = {}
        self.palette: dict[str, str] = {}

    # ---- structural seams -------------------------------------------------- #
    def layer_group(self, inner, layer):
        """The authored layer becomes an addressable, labelled group.

        `<g>` rather than `<section>`: layers live inside the page `<svg>`, where
        HTML sectioning elements are not valid content. The identity survives on
        `data-*`, which is what a consumer actually queries.
        """
        if not inner:
            return inner
        name = layer.get("id") or layer.get("name") if isinstance(layer, dict) else None
        z = layer.get("z") if isinstance(layer, dict) else None
        role = layer.get("role") if isinstance(layer, dict) else None
        attrs = ' class="fg-layer"'
        if name:
            attrs += f' data-layer="{esc(str(name))}"'
        if z is not None:
            attrs += f' data-z="{esc(str(z))}"'
        if role:
            attrs += f' data-role="{esc(str(role))}"'
        return f"<g{attrs}>{inner}</g>"

    def object_group(self, inner, obj):
        """The authored object keeps its `id` and gains a type class.

        Emitted only when there is identity to carry, so an anonymous decorative
        shape does not pay for an extra group.
        """
        if not inner or not isinstance(obj, dict):
            return inner
        oid = obj.get("id")
        otype = obj.get("type")
        if not oid and not otype:
            return inner
        classes = "fg-obj" + (f" fg-{css_ident(otype)}" if otype else "")
        ident = f' id="{esc(str(oid))}"' if oid else ""
        return f'<g{ident} class="{classes}">{inner}</g>'

    # ---- accessibility ----------------------------------------------------- #
    def a11y_wrap(self, inner, obj):
        """Authored semantics first, then the semantics the type implies.

        The SVG backend emits authored fields only. HTML additionally consumes
        the shared `derive_semantics` inference, so a group announces as a group,
        bare connector geometry is hidden instead of announced as an unnamed
        graphic, and a word-glyph icon gets a real name. An author who stated
        anything at all is never overridden.
        """
        authored = SvgPainter.a11y_wrap(inner, obj)
        if authored != inner:
            return authored          # decorative / role / alt / actual_text won
        if not inner or not isinstance(obj, dict):
            return inner

        derived = derive_semantics(obj)
        if not derived:
            return inner
        if derived.get("hidden"):
            return f'<g aria-hidden="true">{inner}</g>'
        label = derived.get("label")
        label_attr = f' aria-label="{esc(label)}"' if label else ""
        title = f"<title>{esc(label)}</title>" if label else ""
        return f'<g role="{esc(derived["role"])}"{label_attr}>{title}{inner}</g>'

    # ---- typography seam --------------------------------------------------- #
    def _text_class_attr(self, st):
        """Reference the hoisted class for a *named* text style.

        The inline `style` the SVG backend emits is kept and still wins the
        cascade — it carries the size the fitter actually resolved, which may
        differ from the style's declared size. The class is the stable hook a
        consumer styles or overrides against; it is not the source of truth.
        """
        ref = st.get("style_ref") if hasattr(st, "get") else None
        if not ref:
            return ""
        ident = css_ident(ref)
        if ident not in self.text_styles:
            self.text_styles[ident] = dict(st)
        return f' class="fg-ts-{ident}"'

    def font_style(self, st, size):
        """Text paint travels in a `style` attribute, where `var()` is reliable,
        so a palette colour is emitted as a themeable custom property with the
        literal as its fallback — themeable when the stylesheet is present,
        correct when it is not."""
        style = SvgPainter.font_style(st, size)
        color = st.get("color") if hasattr(st, "get") else None
        token = self._token(color)
        if token:
            style = style.replace(f"fill:{esc(color)}",
                                  f"fill:var(--fg-{token}, {esc(color)})", 1)
        return style

    # ---- palette collection ------------------------------------------------ #
    def _token(self, literal):
        """The palette token for a resolved literal, recording it for the sheet."""
        name = self._color.token_for(literal) if isinstance(literal, str) else None
        if not name:
            return None
        ident = css_ident(name)
        self.palette.setdefault(ident, literal)
        return ident

    def fill_attr(self, fill, fill_opacity=None, fill_rule=None):
        """Literal paint (see the module's 'Known boundary'), but the token is
        still recorded so the palette reaches the stylesheet."""
        self._token(fill)
        return SvgPainter.fill_attr(fill, fill_opacity, fill_rule)

    # ---- the hoisted stylesheet -------------------------------------------- #
    def stylesheet(self) -> str:
        """The CSS this document needs: the palette, then the named text styles.

        Deterministic: tokens and styles are emitted in first-seen order, so two
        renders of the same document produce byte-identical CSS.
        """
        blocks = []
        if self.palette:
            decls = "".join(f"  --fg-{name}: {value};\n"
                            for name, value in self.palette.items())
            blocks.append(f":root {{\n{decls}}}")
        for ident, st in self.text_styles.items():
            decls = SvgPainter.font_style(st, st.get("size") or 0)
            blocks.append(f".fg-ts-{ident} {{ {decls} }}")
        return "\n".join(blocks)
