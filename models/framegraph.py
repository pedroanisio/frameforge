"""
FrameGraph v2 — HEAD models (the single source of truth).
=========================================================

These Pydantic v2 models are the authoritative definition of the FrameGraph v2
*core conformance profile* at HEAD. Everything else is derived from or checked
against them:

  * schema/framegraph-v2.schema.json  is GENERATED from `Document` (build_schema.py)
  * tooling/validate.py               validates documents against these models + static rules
  * grammar/framegraph-v2.ebnf        is kept consistent by hand (the EBNF is a view, not the source)

This module folds in the full patch series and the complement's recommendations:

  P1  nesting/box-model + text-fit ........ Layout(align/row_gap/column_gap), Style/TextStyle text-fit fields
  P2  assets/media/pattern/captions/spans .. AssetDef, FlowSection.media, Pattern, Caption, grid_span
  P3  stroke single form (BREAKING) ........ Stroke = Color (paint); geometry only in stroke_style; +DimensionObject
  P4  content sizing + font pinning ........ Sizing (field renamed `sizing`), FontDef.hash, validator precondition
  gap#1  the CSS style module .............. `Style` and `BorderSide` are DRAFTED here (harvested from the renderer)

Closed model: every object sets `extra="forbid"`. The visual-object and flowable
unions cover the *implemented* core; the kitchen-sink extended objects (UML zoo,
charts, components, ontology) are intentionally OUT of the core profile and are
reported as warnings by validate.py (the §8.5 conformance mechanism), not modelled
here.

Version of the spec these models target: see fgver.HEAD_VERSION.
"""
from __future__ import annotations

from typing import Annotated, Literal, Optional, Union

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

HEAD_VERSION = "2.2.0"  # v2 line; 2.2.0 adopts the authoritative style module (additive). P3 stroke collapse is the one breaking change (codemod provided).


# --------------------------------------------------------------------------- #
#  Base + scalar value types                                                  #
# --------------------------------------------------------------------------- #
class FG(BaseModel):
    """Closed base: unknown keys are errors (the closed-model decision)."""
    model_config = ConfigDict(extra="forbid")


# A Length is a number (points) or a CSS-ish string ending in a known unit.
# pt/px/mm/in/cm absolute; % and fr are relative (resolved in §3.4/§3.6g).
Length = Union[float, int, str]
Color = str                 # hex (#rgb[a]/#rrggbb[aa]), CSS name, or a tokens.colors key
UnitInterval = Annotated[float, Field(ge=0.0, le=1.0)]
Point = Annotated[list[float], Field(min_length=2, max_length=2)]
Box = Annotated[list[Length], Field(min_length=4, max_length=4)]  # [x, y, w, h], top-left, +y down
Padding = Union[Length, Annotated[list[Length], Field(min_length=1, max_length=4)]]

NumberFormat = Literal["decimal", "lower-roman", "upper-roman", "lower-alpha", "upper-alpha"]
PagePreset = Literal[
    "A3", "A4", "A5", "Letter", "Legal", "Tabloid",
    "deck-16x9", "deck-4x3", "square", "phone", "tablet", "web",
    # Social-media canvases — pixel sizes mirror CanvasResolver.PRESETS.
    "instagram-square", "instagram-portrait", "instagram-landscape", "instagram-story",
    "facebook-post", "facebook-cover", "facebook-story",
    "twitter-post", "twitter-header", "linkedin-post", "linkedin-cover",
    "youtube-thumbnail", "youtube-banner", "tiktok-video", "pinterest-pin",
    "snapchat", "story",
    # Aspect-ratio aliases (canonical canvas at the named ratio).
    "1x1", "4x5", "5x4", "9x16", "16x9", "2x3", "3x2", "1.91x1", "3x1",
]
Units = Literal["pt", "px", "mm", "in", "cm"]
Align = Literal["left", "center", "right"]
VAlign = Literal["top", "middle", "bottom"]


# --------------------------------------------------------------------------- #
#  THE STYLE MODULE (authoritative) — adopted at 2.2.0                        #
#  Faithful translation of grammar/framegraph-v2-style.ebnf. `Style` is the   #
#  CSS-parity bag; TextStyle and StrokeStyle are PROJECTIONS of it; fill/      #
#  stroke are `Paint` (= colour | image | gradient | pattern). `class`         #
#  composes named token styles; `css` is the bounded raw-CSS escape (§8.4).   #
# --------------------------------------------------------------------------- #
Angle = Union[float, int, str]        # number or "<n>deg|rad|grad|turn"
Percentage = str                       # "<n>%"
StrList = Union[str, list[str]]


# ---- paint sources: gradients, patterns, images ----
class GradientStop(FG):
    color: Color
    position: Optional[Union[Length, Percentage]] = None   # authoritative key (was `offset`)

    @model_validator(mode="before")
    @classmethod
    def _accept_offset(cls, v):
        # 2.2.0 flips canonicalisation: `position` is authoritative; accept the
        # legacy `offset` and unit-interval forms, normalised to `position`.
        if isinstance(v, dict) and "position" not in v and "offset" in v:
            v = dict(v)
            o = v.pop("offset")
            v["position"] = (f"{o*100:g}%" if isinstance(o, (int, float)) and o <= 1 else o)
        return v


class Gradient(FG):
    kind: Literal["linear", "radial", "conic"]
    stops: list[GradientStop] = Field(min_length=1)
    repeating: Optional[bool] = None
    angle: Optional[Angle] = None                 # linear
    from_: Optional[Angle] = Field(default=None, alias="from")   # conic start angle
    at: Optional[Union[str, Point]] = None        # radial/conic centre
    shape: Optional[Literal["circle", "ellipse"]] = None
    meta: Optional[dict] = None
    model_config = ConfigDict(extra="forbid", populate_by_name=True)


class Pattern(FG):
    """FG extension paint (P2): tiled hatch/dots/grid, region-clipped."""
    kind: Literal["pattern"]
    pattern: Literal["hatch", "cross_hatch", "dots", "grid"]
    angle: Optional[Angle] = None
    spacing: Optional[Length] = None
    stroke: Optional[Paint] = None
    background: Optional[Color] = None


class UrlImage(FG):
    url: str


Image = Union[Gradient, UrlImage, str]            # url("…")/data-uri/token, or a gradient
Paint = Union[Gradient, Pattern, UrlImage, str]   # "none"|"currentColor"|<color>|<image>|<pattern>


# ---- supporting value types ----
class BorderSide(FG):
    width: Optional[Length] = None
    style: Optional[Literal["none", "hidden", "solid", "dashed", "dotted",
                            "double", "groove", "ridge", "inset", "outset"]] = None
    color: Optional[Color] = None


Border = Union[str, BorderSide]                    # "1px solid #333" or object
Radius = Union[Length, list[Length]]               # 1..4 corners
Edges = Union[Length, list[Length]]                # 1..4 CSS shorthand
SizeValue = Union[Length, Literal["auto", "min-content", "max-content"], dict]
Overflow = Literal["visible", "hidden", "clip", "scroll", "auto"]
BlendMode = Literal["normal", "multiply", "screen", "overlay", "darken", "lighten",
                    "color-dodge", "color-burn", "hard-light", "soft-light", "difference",
                    "exclusion", "hue", "saturation", "color", "luminosity"]
FontStyle = Union[Literal["normal", "italic", "oblique"], dict]
FontStretch = Union[Literal["normal", "ultra-condensed", "extra-condensed", "condensed",
                            "semi-condensed", "semi-expanded", "expanded", "extra-expanded",
                            "ultra-expanded"], str]


class Shadow(FG):
    offset_x: Length
    offset_y: Length
    blur: Optional[Length] = None
    spread: Optional[Length] = None
    color: Optional[Color] = None
    inset: Optional[bool] = None


ShadowVal = Union[str, Shadow]


class FilterFn(FG):
    fn: Literal["blur", "brightness", "contrast", "drop_shadow", "grayscale",
                "hue_rotate", "invert", "opacity", "saturate", "sepia",
                "turbulence", "displacement_map", "diffuse_lighting", "specular_lighting"]
    value: Optional[Union[float, int, str]] = None
    shadow: Optional[ShadowVal] = None
    base_frequency: Optional[Union[float, int, str, list[Union[float, int, str]]]] = None
    num_octaves: Optional[int] = None
    seed: Optional[int] = None
    stitch_tiles: Optional[Literal["stitch", "noStitch"]] = None
    type: Optional[Literal["fractalNoise", "turbulence"]] = None
    mode: Optional[str] = None
    opacity: Optional[Union[float, int, str]] = None
    scale: Optional[Union[float, int, str]] = None
    x_channel: Optional[Literal["R", "G", "B", "A"]] = None
    y_channel: Optional[Literal["R", "G", "B", "A"]] = None
    surface_scale: Optional[Union[float, int, str]] = None
    lighting_color: Optional[Color] = None
    azimuth: Optional[Union[float, int, str]] = None
    elevation: Optional[Union[float, int, str]] = None
    x: Optional[Union[float, int, str]] = None
    y: Optional[Union[float, int, str]] = None
    z: Optional[Union[float, int, str]] = None
    points_at_x: Optional[Union[float, int, str]] = None
    points_at_y: Optional[Union[float, int, str]] = None
    points_at_z: Optional[Union[float, int, str]] = None
    diffuse_constant: Optional[Union[float, int, str]] = None
    specular_constant: Optional[Union[float, int, str]] = None
    specular_exponent: Optional[Union[float, int, str]] = None


Filter = Union[str, list[FilterFn]]


class TransformFn(FG):
    fn: Literal["translate", "translate_x", "translate_y", "scale", "scale_x", "scale_y",
                "rotate", "skew", "skew_x", "skew_y", "matrix"]
    args: list[Union[float, int, str]]


class TextDecoration(FG):
    line: Optional[Union[str, list[str]]] = None
    style: Optional[Literal["solid", "double", "dotted", "dashed", "wavy"]] = None
    color: Optional[Color] = None
    thickness: Optional[Length] = None


TextDecorationVal = Union[str, TextDecoration]


class BackgroundLayer(FG):
    color: Optional[Color] = None
    image: Optional[Image] = None
    position: Optional[str] = None
    size: Optional[Union[Literal["auto", "cover", "contain"], str]] = None
    repeat: Optional[Literal["repeat", "repeat-x", "repeat-y", "no-repeat", "space", "round"]] = None
    clip: Optional[Literal["border-box", "padding-box", "content-box", "text"]] = None


class ClipPath(FG):
    shape: Literal["inset", "circle", "ellipse", "polygon", "path"]
    args: Optional[dict] = None


ClipPathVal = Union[str, ClipPath]


# ---- Style: the umbrella (closed bag of CSS-mapped properties) ----
class Style(FG):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)
    class_: Optional[StrList] = Field(default=None, alias="class")   # ref → tokens.styles
    css: Optional[str] = None                                        # raw-CSS escape (no hard gap)
    # ---- accepted shorthand sugar (desugars to the canonical CSS property; §8.4) ----
    font: Optional[str] = None                 # → font_family
    size: Optional[Length] = None              # → font_size
    weight: Optional[Union[int, str]] = None   # → font_weight
    italic: Optional[bool] = None              # → font_style: italic
    bold: Optional[bool] = None                # → font_weight: bold
    align: Optional[Literal["left", "right", "center", "justify", "start", "end"]] = None  # → text_align
    v_align: Optional[Literal["baseline", "top", "middle", "bottom", "sub", "super"]] = None  # → vertical_align
    radius: Optional[Radius] = None            # → border_radius
    wrap: Optional[bool] = None                # → text_wrap
    # text & font (CSS Text L3 + Fonts L3/L4)
    color: Optional[Color] = None
    font_family: Optional[StrList] = None
    font_size: Optional[Length] = None
    font_weight: Optional[Union[int, Literal["normal", "bold", "lighter", "bolder"]]] = None
    font_style: Optional[FontStyle] = None
    font_stretch: Optional[FontStretch] = None
    font_variant: Optional[str] = None
    font_variant_caps: Optional[Literal["normal", "small-caps", "all-small-caps", "petite-caps",
                                        "all-petite-caps", "unicase", "titling-caps"]] = None
    font_variant_numeric: Optional[str] = None
    font_variant_ligatures: Optional[str] = None
    font_feature_settings: Optional[str] = None
    font_variation_settings: Optional[str] = None
    font_kerning: Optional[Literal["auto", "normal", "none"]] = None
    line_height: Optional[Union[float, int, Length, Literal["normal"]]] = None
    letter_spacing: Optional[Length] = None
    word_spacing: Optional[Length] = None
    text_align: Optional[Literal["left", "right", "center", "justify", "start", "end"]] = None
    text_align_last: Optional[Literal["auto", "left", "right", "center", "justify", "start", "end"]] = None
    vertical_align: Optional[Union[Literal["baseline", "top", "middle", "bottom", "sub", "super"], Length]] = None
    text_decoration: Optional[TextDecorationVal] = None
    text_transform: Optional[Literal["none", "uppercase", "lowercase", "capitalize"]] = None
    text_indent: Optional[Length] = None
    text_shadow: Optional[list[ShadowVal]] = None
    white_space: Optional[Literal["normal", "nowrap", "pre", "pre-wrap", "pre-line", "break-spaces"]] = None
    word_break: Optional[Literal["normal", "break-all", "keep-all", "break-word"]] = None
    overflow_wrap: Optional[Literal["normal", "break-word", "anywhere"]] = None
    hyphens: Optional[Literal["none", "manual", "auto"]] = None
    text_wrap: Optional[Literal["wrap", "nowrap", "balance", "pretty", "stable"]] = None
    hanging_punctuation: Optional[Literal["none", "first", "last", "allow-end", "force-end"]] = None
    hyphenate_character: Optional[str] = None
    hyphenate_limit_chars: Optional[Annotated[list[int], Field(min_length=3, max_length=3)]] = None
    tab_size: Optional[Union[int, Length]] = None
    text_overflow: Optional[Union[Literal["clip", "ellipsis"], str]] = None
    line_clamp: Optional[int] = None
    max_lines: Optional[int] = None
    min_font_size: Optional[float] = None     # +FG text-fit extension (P1; floor for shrink_to_fit). Not a CSS property.
    writing_mode: Optional[Literal["horizontal-tb", "vertical-rl", "vertical-lr"]] = None
    direction: Optional[Literal["ltr", "rtl"]] = None
    unicode_bidi: Optional[Literal["normal", "embed", "isolate", "bidi-override",
                                   "isolate-override", "plaintext"]] = None
    # box, border, overflow (CSS 2.1 box + Backgrounds & Borders L3)
    width: Optional[SizeValue] = None
    height: Optional[SizeValue] = None
    min_width: Optional[SizeValue] = None
    max_width: Optional[SizeValue] = None
    min_height: Optional[SizeValue] = None
    max_height: Optional[SizeValue] = None
    box_sizing: Optional[Literal["content-box", "border-box"]] = None
    padding: Optional[Edges] = None
    margin: Optional[Edges] = None
    border: Optional[Border] = None
    border_top: Optional[BorderSide] = None
    border_right: Optional[BorderSide] = None
    border_bottom: Optional[BorderSide] = None
    border_left: Optional[BorderSide] = None
    border_radius: Optional[Radius] = None
    outline: Optional[BorderSide] = None
    outline_offset: Optional[Length] = None
    overflow: Optional[Literal["visible", "hidden", "clip", "scroll", "auto", "shrink_to_fit"]] = None  # +FG: shrink_to_fit (P1 autofit; P2 Part C)
    overflow_x: Optional[Overflow] = None
    overflow_y: Optional[Overflow] = None
    opacity: Optional[UnitInterval] = None
    visibility: Optional[Literal["visible", "hidden", "collapse"]] = None
    z_index: Optional[int] = None
    # background (multi-layer)
    background: Optional[Union[str, list[BackgroundLayer]]] = None
    background_color: Optional[Color] = None
    background_image: Optional[Union[Image, list[Image]]] = None
    background_position: Optional[str] = None
    background_size: Optional[Union[Literal["auto", "cover", "contain"], str]] = None
    background_repeat: Optional[Literal["repeat", "repeat-x", "repeat-y", "no-repeat", "space", "round"]] = None
    background_clip: Optional[Literal["border-box", "padding-box", "content-box", "text"]] = None
    background_origin: Optional[Literal["border-box", "padding-box", "content-box"]] = None
    background_blend_mode: Optional[BlendMode] = None
    # paint & SVG stroke
    fill: Optional[Paint] = None
    fill_rule: Optional[Literal["nonzero", "evenodd"]] = None
    stroke: Optional[Paint] = None
    stroke_width: Optional[Length] = None
    stroke_dasharray: Optional[Union[Literal["none"], list[Length]]] = None
    stroke_dashoffset: Optional[Length] = None
    stroke_linecap: Optional[Literal["butt", "round", "square"]] = None
    stroke_linejoin: Optional[Literal["miter", "round", "bevel", "arcs", "miter-clip"]] = None
    stroke_miterlimit: Optional[float] = None
    paint_order: Optional[str] = None
    vector_effect: Optional[Literal["none", "non-scaling-stroke"]] = None
    arrow_start: Optional[Union[bool, str]] = None
    arrow_end: Optional[Union[bool, str]] = None
    # effects
    box_shadow: Optional[Union[Literal["none"], list[ShadowVal]]] = None
    filter: Optional[Filter] = None
    backdrop_filter: Optional[Filter] = None
    mix_blend_mode: Optional[BlendMode] = None
    isolation: Optional[Literal["auto", "isolate"]] = None
    clip_path: Optional[ClipPathVal] = None
    mask: Optional[Union[Literal["none"], Image, str]] = None
    # transforms
    transform: Optional[Union[Literal["none"], str, list[TransformFn]]] = None
    transform_origin: Optional[Union[str, Point]] = None
    transform_box: Optional[Literal["border-box", "fill-box", "view-box", "content-box"]] = None
    perspective: Optional[Union[Literal["none"], Length]] = None


# TextStyle and StrokeStyle are PROJECTIONS of Style (the module's contract).
TextStyle = Style
StrokeStyle = Style
StyleRef = Union[str, Style]
Fill = Paint                                       # fill is a Paint
StrokeStyleRef = Union[str, Style]                 # a named stroke bundle is a Style


# --------------------------------------------------------------------------- #
#  Fonts, assets                                                              #
# --------------------------------------------------------------------------- #
class FontDef(FG):
    family: str
    src: Optional[str] = None
    hash: Optional[str] = None         # +HEAD: content hash; required to pin a font (P4 Part C)
    fallback: Optional[list[str]] = None
    weight: Optional[Union[int, str]] = None
    style: Optional[Literal["normal", "italic", "oblique"]] = None


FontDefOrName = Union[str, FontDef]


class AssetDef(FG):
    src: str
    hash: Optional[str] = None
    kind: Optional[Literal["image", "icon_font", "font", "data"]] = None
    media_type: Optional[str] = None


# --------------------------------------------------------------------------- #
#  Layout + content sizing (P1 + P4)                                          #
# --------------------------------------------------------------------------- #
class Layout(FG):
    kind: Literal["row", "column", "grid", "wrap", "free"]
    gap: Optional[Length] = None
    row_gap: Optional[Length] = None
    column_gap: Optional[Length] = None
    padding: Optional[Padding] = None
    columns: Optional[int] = None
    align: Optional[Literal["start", "center", "end", "stretch"]] = None
    justify: Optional[Literal["start", "center", "end", "space-between", "space-around", "space-evenly"]] = None


SizeMode = Literal["fixed", "hug", "fill"]


class Sizing(FG):
    """P4 content sizing. The field on objects is `sizing` (renamed from `size`
    to resolve the collision with IconObject.size)."""
    width: Optional[SizeMode] = None
    height: Optional[SizeMode] = None
    grow: Optional[float] = None
    min: Optional[Annotated[list[Length], Field(min_length=2, max_length=2)]] = None
    max: Optional[Annotated[list[Length], Field(min_length=2, max_length=2)]] = None


class ClipSpec(FG):
    shape: Literal["rect", "ellipse", "path"]
    radius: Optional[Length] = None


ClipSpecOrBool = Union[bool, ClipSpec]


class Rotation(FG):
    angle: float
    center: Optional[Point] = None


RotationOrNumber = Union[float, int, Rotation]


class EffectObject(FG):
    color: Optional[Color] = None
    blur: Optional[float] = None
    dx: Optional[float] = None
    dy: Optional[float] = None
    opacity: Optional[UnitInterval] = None


Effect = Union[str, bool, EffectObject]


class OuterRing(FG):
    color: Optional[Color] = None
    width: Optional[float] = None
    gap: Optional[float] = None
    offset: Optional[float] = None
    dash: Optional[Union[list[float], str]] = None
    opacity: Optional[UnitInterval] = None


class AnchorObject(FG):
    ref: str
    port: Optional[str] = None


Anchor = Union[str, Point, AnchorObject]


class Number(FG):
    series: str
    parent: Optional[str] = None
    reset_with: Optional[str] = None
    format: Optional[NumberFormat] = None
    prefix: Optional[str] = None
    suffix: Optional[str] = None


# --------------------------------------------------------------------------- #
#  Inline content                                                             #
# --------------------------------------------------------------------------- #
class Span(FG):
    text: str
    style: Optional[StyleRef] = None
    lang: Optional[str] = None


class RefInline(FG):
    kind: Literal["ref"]
    target: str
    show: Optional[Literal["auto", "number", "page", "label", "title"]] = None


class CiteInline(FG):
    kind: Literal["cite"]
    key: Union[str, list[str]]
    mode: Optional[Literal["parenthetical", "textual", "author", "year", "note"]] = None
    locator: Optional[str] = None
    prefix: Optional[str] = None
    suppress_author: Optional[bool] = None


class MathInline(FG):
    kind: Literal["math"]
    mathml: Optional[str] = None
    tex: Optional[str] = None


class CodeInline(FG):
    kind: Literal["code"]
    text: str


class FootnoteInline(FG):
    kind: Literal["footnote"]
    content: list["Flowable"]
    placement: Optional[Literal["footnote", "endnote"]] = None
    id: Optional[str] = None


class LinkInline(FG):
    kind: Literal["link"]
    href: str
    content: list["Inline"]
    title: Optional[str] = None


Inline = Union[str, RefInline, CiteInline, MathInline, CodeInline, FootnoteInline, LinkInline, Span]
Caption = Union[str, list[Inline]]


# --------------------------------------------------------------------------- #
#  common-object-fields (mixin) + stroke single-form enforcement              #
# --------------------------------------------------------------------------- #
class ObjBase(FG):
    id: Optional[str] = None
    box: Optional[Box] = None
    rotation: Optional[RotationOrNumber] = None
    ports: Optional[dict[str, Point]] = None
    bind: Optional[str] = None
    decorative: Optional[bool] = None
    z: Optional[float] = None
    opacity: Optional[UnitInterval] = None
    fill_opacity: Optional[UnitInterval] = None
    stroke_opacity: Optional[UnitInterval] = None
    stroke_style: Optional[StrokeStyleRef] = None     # P3: the single home for stroke geometry (token or inline)
    style: Optional[StyleRef] = None
    shadow: Optional[Effect] = None
    glow: Optional[Effect] = None
    outer_ring: Optional[OuterRing] = None
    grid_span: Optional[Annotated[list[int], Field(min_length=2, max_length=2)]] = None
    sizing: Optional[Sizing] = None                   # P4 (renamed from `size`)
    meta: Optional[dict] = None

    @model_validator(mode="before")
    @classmethod
    def _stroke_paint_only(cls, data):
        # P3 BREAKING: an inline-geometry `stroke` object is removed. Catch it with
        # an actionable error pointing at the codemod, instead of a vague type error.
        # Runs before field validation so it fires for every visual object subclass.
        sv = data.get("stroke") if isinstance(data, dict) else None
        if isinstance(sv, dict) and any(k in sv for k in ("width", "dash", "linecap", "linejoin")):
            raise ValueError(
                "stroke is paint-only (P3): an inline geometry object {color,width,dash,...} "
                "is not allowed. Put paint in `stroke` (a colour/gradient/pattern) and geometry "
                "in `stroke_style` (a named Style). Run tooling/codemod.py to migrate."
            )
        return data


# --------------------------------------------------------------------------- #
#  Visual objects (core profile + DimensionObject; renderer-shortcut aliases) #
# --------------------------------------------------------------------------- #
class Rect(ObjBase):
    type: Literal["rect"]
    fill: Optional[Paint] = None
    radius: Optional[Length] = None
    stroke: Optional[Paint] = None


class Ellipse(ObjBase):
    type: Literal["ellipse"]
    center: Point
    rx: float
    ry: float
    fill: Optional[Fill] = None
    stroke: Optional[Paint] = None


class Circle(ObjBase):
    """Renderer-shortcut alias for an ellipse with rx==ry. Deprecated at HEAD;
    the codemod normalises it to `ellipse`."""
    type: Literal["circle"]
    center: Point
    r: float
    fill: Optional[Fill] = None
    stroke: Optional[Paint] = None


class Line(ObjBase):
    type: Literal["line"]
    from_: Anchor = Field(alias="from")
    to: Anchor
    stroke: Optional[Paint] = None
    model_config = ConfigDict(extra="forbid", populate_by_name=True)


class Polyline(ObjBase):
    type: Literal["polyline"]
    points: list[Point] = Field(min_length=2)
    closed: Optional[bool] = None
    fill: Optional[Fill] = None
    stroke: Optional[Paint] = None


class Polygon(ObjBase):
    """Renderer-shortcut alias for a closed polyline. Deprecated; codemod normalises."""
    type: Literal["polygon"]
    points: list[Point] = Field(min_length=3)
    fill: Optional[Fill] = None
    stroke: Optional[Paint] = None


# --------------------------------------------------------------------------- #
#  Path segment algebra (G-1)                                                   #
# --------------------------------------------------------------------------- #
# A path's `d` may be either the SVG path-data string (the compiled view) or a
# structured list of typed segments — one SVG command per segment, `[cmd, *coords]`.
# Lowercase command letters are relative, uppercase absolute (mirroring SVG path
# data). Typing each segment is what lets the JSON Schema validate geometry shape
# and arity instead of accepting an opaque array; the `d` string remains the
# compiled view of the same geometry (roadmap item G-1).
PathCommand = Literal[
    "M", "m", "L", "l", "H", "h", "V", "v",
    "C", "c", "S", "s", "Q", "q", "T", "t", "A", "a", "Z", "z",
]

_SegMove = tuple[Literal["M", "m"], float, float]                      # moveto x y
_SegLine = tuple[Literal["L", "l"], float, float]                      # lineto x y
_SegHoriz = tuple[Literal["H", "h"], float]                            # horizontal x
_SegVert = tuple[Literal["V", "v"], float]                             # vertical y
_SegCubic = tuple[Literal["C", "c"], float, float, float, float, float, float]  # x1 y1 x2 y2 x y
_SegSmooth = tuple[Literal["S", "s"], float, float, float, float]      # x2 y2 x y
_SegQuad = tuple[Literal["Q", "q"], float, float, float, float]        # x1 y1 x y
_SegTquad = tuple[Literal["T", "t"], float, float]                     # x y
_SegArc = tuple[Literal["A", "a"], float, float, float, float, float, float, float]  # rx ry rot large sweep x y
_SegClose = tuple[Literal["Z", "z"]]                                   # closepath

# One typed segment: the first element is the command, the rest its coordinates.
PathSeg = Union[
    _SegMove, _SegLine, _SegHoriz, _SegVert, _SegCubic,
    _SegSmooth, _SegQuad, _SegTquad, _SegArc, _SegClose,
]


class Path(ObjBase):
    type: Literal["path"]
    # SVG `d` string, or structured `[[cmd, *coords], ...]` segments (G-1).
    d: Union[str, list[PathSeg]] = Field(union_mode="left_to_right")
    fill: Optional[Fill] = None
    stroke: Optional[Paint] = None


class Curve(ObjBase):
    """Renderer-shortcut alias for a single cubic Bézier. Deprecated; codemod → path."""
    type: Literal["curve", "bezier"]
    from_: Point = Field(alias="from")
    to: Point
    control1: Optional[Point] = None
    control2: Optional[Point] = None
    c1: Optional[Point] = None
    c2: Optional[Point] = None
    stroke: Optional[Paint] = None
    fill: Optional[Fill] = None
    model_config = ConfigDict(extra="forbid", populate_by_name=True)


class Text(ObjBase):
    type: Literal["text"]
    text: Optional[str] = None
    spans: Optional[list[Inline]] = None
    field: Optional[Union[Literal["page", "pages"], dict]] = None

    @model_validator(mode="after")
    def _one_of_text_spans(self):
        if (self.text is None) == (self.spans is None):
            raise ValueError("a text object needs exactly one of `text` or `spans`")
        return self


class Image(ObjBase):
    type: Literal["image"]
    src: str
    alt: Optional[str] = None
    actual_text: Optional[str] = None
    placeholder: Optional[bool] = None
    preserve_aspect_ratio: Optional[Union[bool, str]] = None   # bool or SVG preserveAspectRatio string
    clip: Optional[Union[bool, str, ClipSpec]] = None
    radius: Optional[Length] = None
    label: Optional[str] = None


class Icon(ObjBase):
    type: Literal["icon"]
    glyph: str
    color: Optional[Color] = None
    font: Optional[str] = None
    size: Optional[float] = None              # NB: icon keeps `size`; content sizing is `sizing`


class BulletList(ObjBase):
    type: Literal["bullet_list"]
    items: list[Union[str, Span]]
    marker: Optional[str] = None
    marker_color: Optional[Color] = None
    gap: Optional[float] = None
    indent: Optional[float] = None


class Dimension(ObjBase):
    """P3 §3.10 composite anchored dimension."""
    type: Literal["dimension"]
    kind: Literal["linear", "aligned", "angular", "radial", "diameter"]
    from_: Anchor = Field(alias="from")
    to: Anchor
    value: Optional[Union[float, Literal["auto"]]] = None
    text: Optional[str] = None
    prefix: Optional[str] = None
    suffix: Optional[str] = None
    offset: Optional[Length] = None
    arrows: Optional[Literal["both", "first", "second", "none"]] = None
    text_style: Optional[str] = None
    model_config = ConfigDict(extra="forbid", populate_by_name=True)


class Cell(FG):
    content: str
    style: Optional[StyleRef] = None
    span: Optional[Annotated[list[int], Field(min_length=2, max_length=2)]] = None


CellValue = Union[str, float, int, bool, None, Span, Cell]


class ColumnSpec(FG):
    label: Optional[str] = None
    width: Optional[Length] = None
    align: Optional[Align] = None


ColumnSpecVal = Union[str, ColumnSpec]


class TableObject(ObjBase):
    type: Literal["table"]
    rows: list[list[CellValue]]
    columns: Optional[list[ColumnSpecVal]] = None
    header: Optional[list[CellValue]] = None
    row_height: Optional[Length] = None
    header_height: Optional[Length] = None
    zebra: Optional[bool] = None
    cell_padding: Optional[Union[Length, list[Length]]] = None
    style: Optional[Union[str, dict]] = None        # grammar: object-any


class Group(ObjBase):
    type: Literal["group"]
    children: list["VisualObject"]
    layout: Optional[Layout] = None


VisualObject = Annotated[
    Union[
        Rect, Ellipse, Circle, Line, Polyline, Polygon, Path, Curve,
        Text, Image, Icon, BulletList, Dimension, TableObject, Group,
    ],
    Field(discriminator="type"),
]


# --------------------------------------------------------------------------- #
#  Flowables (story content)                                                  #
# --------------------------------------------------------------------------- #
class BreakFields(FG):
    break_before: Optional[Literal["auto", "always", "avoid", "page", "column"]] = None
    break_after: Optional[Literal["auto", "always", "avoid", "page", "column"]] = None
    break_inside: Optional[Literal["auto", "avoid", "avoid-page", "avoid-column"]] = None


class StringSet(FG):
    name: str
    value: Optional[str] = None


class ParagraphFlow(BreakFields):
    type: Literal["paragraph"]
    text: Optional[str] = None
    spans: Optional[list[Inline]] = None
    style: Optional[StyleRef] = None
    lang: Optional[str] = None
    widows: Optional[int] = None
    orphans: Optional[int] = None

    @model_validator(mode="after")
    def _one_of(self):
        if (self.text is None) == (self.spans is None):
            raise ValueError("a paragraph needs exactly one of `text` or `spans`")
        return self


class HeadingFlow(BreakFields):
    type: Literal["heading"]
    level: int
    text: str
    id: Optional[str] = None
    number: Optional[Number] = None
    set_string: Optional[list[StringSet]] = None
    lang: Optional[str] = None
    style: Optional[StyleRef] = None


class ListItemFlow(FG):
    text: Optional[str] = None
    spans: Optional[list[Inline]] = None
    style: Optional[StyleRef] = None


ListItemVal = Union[str, ListItemFlow, list["ParagraphFlow"]]


class ListFlow(BreakFields):
    type: Literal["list"]
    items: list[ListItemVal]
    ordered: Optional[bool] = None
    marker: Optional[str] = None
    style: Optional[StyleRef] = None


class SpacerFlow(FG):
    type: Literal["spacer"]
    height: Optional[Length] = None


class PageBreakFlow(FG):
    type: Literal["page_break"]


class ColumnBreakFlow(FG):
    type: Literal["column_break"]


class TableFlow(BreakFields):
    type: Literal["table"]
    rows: list[list[CellValue]]
    columns: Optional[list[ColumnSpecVal]] = None
    header: Optional[list[CellValue]] = None
    row_height: Optional[Length] = None
    header_height: Optional[Length] = None
    zebra: Optional[bool] = None
    cell_padding: Optional[Union[Length, list[Length]]] = None
    style: Optional[Union[str, dict]] = None        # grammar: object-any
    caption: Optional[Caption] = None
    credit: Optional[Caption] = None
    id: Optional[str] = None
    number: Optional[Number] = None


class ImageFlow(BreakFields):
    type: Literal["image"]
    src: str
    alt: Optional[str] = None
    actual_text: Optional[str] = None
    width: Optional[Length] = None
    height: Optional[Length] = None
    preserve_aspect_ratio: Optional[Union[bool, str]] = None
    caption: Optional[Caption] = None
    credit: Optional[Caption] = None


class FigureFlow(BreakFields):
    type: Literal["figure"]
    object: "VisualObject"
    alt: Optional[str] = None
    actual_text: Optional[str] = None
    align: Optional[Literal["left", "center", "right"]] = None
    units: Optional[Units] = None        # coordinate unit of the figure's drawing space (default px)
    size: Optional[Annotated[list[Length], Field(min_length=2, max_length=2)]] = None
    caption: Optional[Caption] = None
    credit: Optional[Caption] = None
    id: Optional[str] = None
    number: Optional[Number] = None


class BlockFlow(BreakFields):
    type: Literal["block"]
    children: list["Flowable"]
    style: Optional[StyleRef] = None
    role: Optional[str] = None
    fill: Optional[Fill] = None
    stroke: Optional[Paint] = None
    stroke_style: Optional[StrokeStyleRef] = None
    padding: Optional[Edges] = None
    id: Optional[str] = None


class KeepTogetherFlow(BreakFields):
    type: Literal["keep_together"]
    children: list["Flowable"]


class CodeFlow(BreakFields):
    type: Literal["code"]
    source: str
    language: Optional[str] = None
    line_numbers: Optional[bool] = None
    style: Optional[StyleRef] = None


class MathFlow(BreakFields):
    type: Literal["math"]
    tex: Optional[str] = None
    mathml: Optional[str] = None
    alt: Optional[str] = None        # plain-text fallback for accessibility (a11y/tagged export)
    id: Optional[str] = None
    number: Optional[Number] = None


class TocFlow(BreakFields):
    type: Literal["toc"]
    of: Optional[Literal["headings", "figures", "tables", "equations", "listings"]] = None
    levels: Optional[list[int]] = None
    title: Optional[str] = None
    style: Optional[StyleRef] = None
    leader: Optional[str] = None


class BibliographyFlow(BreakFields):
    type: Literal["bibliography"]
    title: Optional[str] = None
    source: Optional[str] = None
    csl: Optional[str] = None
    entries: Optional[list[dict]] = None
    id: Optional[str] = None


Flowable = Annotated[
    Union[
        ParagraphFlow, HeadingFlow, ListFlow, SpacerFlow, PageBreakFlow, ColumnBreakFlow,
        TableFlow, ImageFlow, FigureFlow, BlockFlow, KeepTogetherFlow,
        CodeFlow, MathFlow, TocFlow, BibliographyFlow,
    ],
    Field(discriminator="type"),
]


# --------------------------------------------------------------------------- #
#  Pages, masters, canvas                                                     #
# --------------------------------------------------------------------------- #
class CanvasObject(FG):
    preset: Optional[PagePreset] = None
    size: Optional[Annotated[list[float], Field(min_length=2, max_length=2)]] = None
    units: Optional[Units] = None
    orientation: Optional[Literal["portrait", "landscape"]] = None
    bleed: Optional[Length] = None
    margin: Optional[Box] = None

    @model_validator(mode="after")
    def _preset_or_size(self):
        if (self.preset is None) == (self.size is None):
            raise ValueError("a canvas object needs exactly one of `preset` or `size`")
        return self


CanvasSpec = Union[PagePreset, CanvasObject]


class FlowRegion(FG):
    id: str
    box: Box
    columns: Optional[int] = None
    column_gap: Optional[Length] = None
    column_fill: Optional[Literal["auto", "balance"]] = None
    column_rule: Optional[BorderSide] = None
    next: Optional[str] = None


class Running(FG):
    header: Optional[list[VisualObject]] = None
    footer: Optional[list[VisualObject]] = None
    page_number: Optional[Union[bool, Style]] = None


class PageMaster(FG):
    canvas: CanvasSpec
    margin: Optional[Box] = None
    fixed: Optional[list[VisualObject]] = None
    regions: Optional[list[FlowRegion]] = None
    running: Optional[Running] = None
    footnote_area: Optional[FlowRegion] = None
    next: Optional[str] = None


class Layer(FG):
    id: str
    z: Optional[float] = None
    opacity: Optional[UnitInterval] = None
    objects: Optional[list[VisualObject]] = None


class TextContract(FG):
    min_font_size: Optional[float] = None
    overflow: Optional[Literal["visible", "clip", "shrink_to_fit"]] = None
    line_clamp: Optional[int] = None
    text_overflow: Optional[Literal["clip", "ellipsis"]] = None


class RenderingContract(FG):
    coordinate_mode: Optional[Literal["absolute", "flow"]] = None
    text: Optional[TextContract] = None
    typography: Optional[dict] = None
    semantics: Optional[dict] = None
    debug_boxes: Optional[bool] = None
    preserve_manual_line_breaks: Optional[bool] = None


class PageLink(FG):
    to: str
    relation: Optional[Literal["next", "prev", "see_also", "appendix", "source", "child", "parent", "external"]] = None
    label: Optional[str] = None
    external: Optional[bool] = None


class Page(FG):
    mode: Literal["page"]
    id: str
    master: Optional[str] = None
    canvas: Optional[CanvasSpec] = None
    rendering: Optional[RenderingContract] = None
    layers: Optional[list[Layer]] = None
    reading_order: Optional[list[str]] = None
    semantic: Optional[dict] = None
    links: Optional[list[PageLink]] = None
    notes: Optional[str] = None
    meta: Optional[dict] = None


class FlowSection(FG):
    mode: Literal["flow"]
    id: str
    master: str
    story: list[Flowable]
    media: Optional[Literal["paged", "continuous"]] = None
    page_numbering: Optional[dict] = None
    lang: Optional[str] = None
    links: Optional[list[PageLink]] = None        # section-level navigation, mirroring Page.links
    semantic: Optional[dict] = None
    meta: Optional[dict] = None


PageProducer = Annotated[Union[Page, FlowSection], Field(discriminator="mode")]


# --------------------------------------------------------------------------- #
#  Tokens, defs, targets, document root                                       #
# --------------------------------------------------------------------------- #
class CounterDef(FG):
    start: Optional[int] = None
    reset_with: Optional[str] = None
    format: Optional[NumberFormat] = None


class Tokens(FG):
    colors: Optional[dict[str, Color]] = None
    fonts: Optional[dict[str, FontDefOrName]] = None
    text_styles: Optional[dict[str, Style]] = None     # superseded by Style (gap #1 resolved)
    styles: Optional[dict[str, Style]] = None
    stroke_styles: Optional[dict[str, StrokeStyle]] = None
    fill_styles: Optional[dict[str, Fill]] = None
    glyph_map: Optional[dict[str, str]] = None


class Defs(FG):
    tokens: Optional[Tokens] = None
    counters: Optional[dict[str, CounterDef]] = None
    masters: Optional[dict[str, PageMaster]] = None
    assets: Optional[dict[str, AssetDef]] = None
    data: Optional[dict] = None                         # CSL-JSON sources etc.
    # Grammar-allowed but OUT of the deep core profile — accepted loosely so they
    # are not hard errors; validate.py reports their presence as a warning.
    symbols: Optional[dict] = None
    components: Optional[dict] = None
    ontology: Optional[dict] = None


class TargetAdjustments(FG):
    font_scale: Optional[float] = None
    hide: Optional[list[str]] = None
    padding_delta: Optional[float] = None


class RenderTarget(FG):
    name: str
    canvas: CanvasSpec
    adjustments: Optional[TargetAdjustments] = None


SEMVER_RE = r"^\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?(?:\+[0-9A-Za-z.-]+)?$"


class Document(FG):
    dsl: Literal["FrameGraph"]
    version: Annotated[str, Field(pattern=SEMVER_RE)]
    profile: Optional[Literal["deck", "book", "letter", "report", "diagram", "mixed"]] = None
    title: Optional[str] = None
    description: Optional[str] = None
    lang: Optional[str] = None
    defs: Optional[Defs] = None
    targets: Optional[list[RenderTarget]] = None
    pages: list[PageProducer] = Field(min_length=1)
    meta: Optional[dict] = None
    text_contract: Optional[TextContract] = None       # accepted at top level (renderer convenience)


# Resolve forward references (recursive groups, footnotes-in-spans, blocks).
for _m in (
    Style, Gradient, GradientStop, FootnoteInline, LinkInline, Group, Text, FigureFlow, BlockFlow,
    KeepTogetherFlow, ListFlow, Running, PageMaster, Layer,
):
    _m.model_rebuild()
Document.model_rebuild()


__all__ = ["Document", "HEAD_VERSION"]
