"""
HTML DocumentRenderer backend
=============================

Rebuild an HTML page from a FrameForge v2 document (the `diagram` profile:
canvas + layers + absolutely-positioned objects).

This is the HTML adapter of the `DocumentRenderer` output port
(``frameforge.rendering.domain.ports``): the pure `render_document(doc) -> str`
transform below, wrapped by `HtmlDocumentRenderer` at the foot of the module.
It moved here from ``tooling/frameforge_to_html.py`` so the render pipeline
reaches it *in-process* through the port instead of the CLI subprocessing a
script. `load_document` / `maybe_validate` remain as convenience loaders; the
CLI parses the document and calls `render` directly.

The output is *layered* and *semantically named*:

  * each page is a ``<figure>`` carrying a ``<figcaption>`` that labels it
  * one ``<section class="fg-layer" data-layer="...">`` per layer, stacked by ``z``
  * ``group`` objects become nested ``<div class="fg-group" role="group">``
  * every object keeps its FrameForge ``id`` as the DOM ``id``
  * palette colors become ``:root`` CSS variables  (``--fg-event_blue`` ...)
  * each ``text_styles`` entry becomes a ``.fg-ts-<name>`` CSS class

Accessibility is derived from the model, not guessed:

  * the document gets a visually-hidden ``<h1>`` (its title) as a landmark
  * ``decorative`` objects (and their subtrees) are hidden via ``aria-hidden``
  * icons and image placeholders expose an accessible name when one can be
    derived (``role="img"`` + ``aria-label``); otherwise they are hidden
  * connector geometry (``line`` SVG) is marked ``aria-hidden``

So the generated markup reads back like the source graph rather than a wall
of anonymous ``<div>``s.

Scope
-----
This renders the *canvas / diagram* side of the schema (``coordinate_mode:
absolute``): rect, text, icon, ellipse, circle, line, polyline, polygon,
path, curve/bezier, image, group — with the row / column / grid / wrap / free
layouts. Canvas size is resolved from an inline ``size`` or a named preset
(``A4``, ``deck-16x9`` ...).

The *document/flow* profile (paragraphs, headings, tables, TOC, ``mode:
flow`` ...) is out of scope: a ``flow`` page becomes a labelled placeholder
and the still-unsupported object types (table, bullet_list, dimension) are
emitted as labelled placeholders — never silently dropped. Gradient ``fill``
paints render for real (a CSS gradient on div shapes, an SVG gradient ``<defs>``
on inline shapes); only ``pattern`` paints still degrade to a flat colour.

Usage
-----
    python -m frameforge.cli input.fg.yaml --to html      # the front door
    # or, in process:
    from frameforge.rendering.infrastructure.backends.html import render_document
    html_text = render_document(doc_dict)

YAML input needs PyYAML; JSON input needs nothing extra.
"""

from __future__ import annotations

import html
import json
import math
import os
import re
import sys
from typing import Any, Iterable

from frameforge.rendering.domain.ports import RenderedArtifact
from frameforge.rendering.domain.services.canvas_resolver import (
    CanvasResolver as _CanvasResolver,
    DEFAULT_WH as _HTML_DEFAULT_WH,
    # Shared-identity gate symbol (drift-risk-map #4, tests/test_frameforge_to_html.py):
    # `canvas_size` resolves through _CanvasResolver, which reads this SAME table.
    PRESETS as _CANVAS_PRESETS,  # noqa: F401
)

# --------------------------------------------------------------------------- #
# Loading                                                                      #
# --------------------------------------------------------------------------- #


def load_document(path: str) -> dict:
    """Load a FrameForge document from YAML or JSON."""
    with open(path, "r", encoding="utf-8") as fh:
        text = fh.read()
    if path.lower().endswith((".yaml", ".yml")):
        try:
            import yaml
        except ImportError as exc:  # pragma: no cover
            raise SystemExit(
                "PyYAML is required for YAML input: pip install pyyaml"
            ) from exc
        return yaml.safe_load(text)
    return json.loads(text)


def maybe_validate(doc: dict, schema_path: str | None) -> None:
    """Validate against the JSON Schema if jsonschema is installed."""
    if not schema_path:
        return
    try:
        import jsonschema
    except ImportError:
        print(
            "  note: jsonschema not installed; skipping validation "
            "(pip install jsonschema)",
            file=sys.stderr,
        )
        return
    with open(schema_path, "r", encoding="utf-8") as fh:
        schema = json.load(fh)
    errors = sorted(
        jsonschema.Draft202012Validator(schema).iter_errors(doc),
        key=lambda e: list(e.path),
    )
    if not errors:
        print("  schema: OK", file=sys.stderr)
        return
    print(f"  schema: {len(errors)} issue(s) (rendering anyway):", file=sys.stderr)
    for err in errors[:20]:
        loc = "/".join(str(p) for p in err.path) or "<root>"
        print(f"    - {loc}: {err.message}", file=sys.stderr)
    if len(errors) > 20:
        print(f"    ... and {len(errors) - 20} more", file=sys.stderr)


# --------------------------------------------------------------------------- #
# Token resolution                                                             #
# --------------------------------------------------------------------------- #


class Tokens:
    """Resolves token names (colors, fonts, styles, glyphs) from ``defs``."""

    def __init__(self, doc: dict):
        defs = (doc.get("defs") or {})
        tok = (defs.get("tokens") or {})
        self.colors: dict[str, str] = tok.get("colors") or {}
        self.fonts: dict[str, Any] = tok.get("fonts") or {}
        # `styles` is the live bucket; `text_styles` is the superseded alias
        # (frameforge.model Tokens). Merge both so a `style:` name reference
        # always resolves to a generated `.fg-ts-<name>` class, with `styles`
        # winning on a name collision.
        self.text_styles: dict[str, dict] = {
            **(tok.get("text_styles") or {}),
            **(tok.get("styles") or {}),
        }
        self.stroke_styles: dict[str, dict] = tok.get("stroke_styles") or {}
        self.glyph_map: dict[str, str] = tok.get("glyph_map") or {}

    # -- colors ------------------------------------------------------------- #
    def color(self, value: Any) -> str | None:
        """A token name -> ``var(--fg-name)``; a literal color passes through."""
        if value is None or not isinstance(value, str):
            return value if value is None else str(value)
        if value in self.colors:
            return f"var(--fg-{_css_ident(value)})"
        return value  # already a literal hex / css color / gradient handled elsewhere

    def color_literal(self, value: Any) -> str | None:
        """Resolve a token to its raw hex (used for SVG attributes)."""
        if isinstance(value, str) and value in self.colors:
            return self.colors[value]
        return value

    # -- fonts -------------------------------------------------------------- #
    def font_stack(self, name: Any) -> str | None:
        """Resolve a font name into a CSS ``font-family`` stack.

        ``name`` may be a single token/family (``str``) or a family list
        (``StrList`` — e.g. ``["Inter", "sans-serif"]``, the Style model's
        ``font_family``). Each entry that names a ``defs.tokens.fonts`` token
        is expanded to its family + fallbacks; anything else is a literal.
        """
        if not name:
            return None
        names = list(name) if isinstance(name, (list, tuple)) else [name]
        families: list[str] = []
        for n in names:
            spec = self.fonts.get(n) if isinstance(n, str) else None
            if spec:
                families.append(spec.get("family", n))
                families.extend(spec.get("fallback") or [])
            elif n:
                families.append(str(n))
        if not families:
            return None
        return ", ".join(_quote_family(f) for f in families)

    # -- glyphs ------------------------------------------------------------- #
    def glyph(self, name: str) -> str:
        return self.glyph_map.get(name, name)


def _quote_family(fam: str) -> str:
    generic = {"serif", "sans-serif", "monospace", "cursive", "fantasy", "system-ui"}
    return fam if fam in generic else f"'{fam}'"


def _css_ident(name: str) -> str:
    ident = re.sub(r"[^A-Za-z0-9_-]", "-", str(name))
    if not re.match(r"[A-Za-z_-]", ident):
        ident = "x-" + ident
    return ident


def _icon_label(glyph_name: str) -> str | None:
    """Humanize a glyph *token name* into an accessible label.

    A word-like token (``calendar-check`` -> "calendar check") names the icon
    for assistive tech. A raw symbol/emoji glyph, or a token with no letters,
    carries no standalone meaning -> return ``None`` so the caller hides it.
    """
    if not glyph_name or not re.search(r"[A-Za-z]", glyph_name):
        return None
    if len(glyph_name) <= 2:  # likely a literal glyph char, not a name
        return None
    return re.sub(r"[\s_-]+", " ", glyph_name).strip() or None


# --------------------------------------------------------------------------- #
# Geometry helpers                                                             #
# --------------------------------------------------------------------------- #


def _num(v: Any, default: float = 0.0) -> float:
    """Best-effort number from int/float/str ('12', '12px')."""
    if isinstance(v, (int, float)):
        return float(v)
    if isinstance(v, str):
        m = re.match(r"^\s*(-?\d+(?:\.\d+)?)", v)
        if m:
            return float(m.group(1))
    return default


def _box(obj: dict) -> tuple[float, float, float, float]:
    b = obj.get("box") or [0, 0, 0, 0]
    b = list(b) + [0, 0, 0, 0]
    return _num(b[0]), _num(b[1]), _num(b[2]), _num(b[3])


def _pad(value: Any) -> tuple[float, float, float, float]:
    """Normalize padding (scalar | [v,h] | [t,r,b,l]) to (t,r,b,l)."""
    if value is None:
        return (0, 0, 0, 0)
    if isinstance(value, (int, float, str)):
        p = _num(value)
        return (p, p, p, p)
    vals = [_num(x) for x in value]
    if len(vals) == 1:
        p = vals[0]
        return (p, p, p, p)
    if len(vals) == 2:
        v, h = vals
        return (v, h, v, h)
    if len(vals) == 3:
        t, h, b = vals
        return (t, h, b, h)
    return (vals[0], vals[1], vals[2], vals[3])


def _obj_size(obj: dict) -> tuple[float, float]:
    """Width/height of an object for layout purposes (handles shape-anchored types)."""
    t = obj.get("type")
    if t == "ellipse":
        return 2 * _num(obj.get("rx")), 2 * _num(obj.get("ry"))
    if t == "circle":
        return 2 * _num(obj.get("r")), 2 * _num(obj.get("r"))
    if t == "line":
        (x1, y1), (x2, y2) = _line_points(obj)
        return abs(x2 - x1), abs(y2 - y1)
    if t in ("polyline", "polygon"):
        pts = _points(obj.get("points"))
        if pts:
            minx, miny, maxx, maxy = _bbox(pts)
            return maxx - minx, maxy - miny
    if t in ("curve", "bezier"):
        pts = [_point(obj.get("from")), _point(obj.get("to")),
               _point(obj.get("control1") or obj.get("c1") or obj.get("from")),
               _point(obj.get("control2") or obj.get("c2") or obj.get("to"))]
        minx, miny, maxx, maxy = _bbox(pts)
        return maxx - minx, maxy - miny
    _, _, w, h = _box(obj)
    return w, h


def _line_points(obj: dict):
    def pt(p):
        if isinstance(p, (list, tuple)):
            return _num(p[0]), _num(p[1])
        return 0.0, 0.0  # string anchors / AnchorObject not supported in absolute mode

    return pt(obj.get("from")), pt(obj.get("to"))


def _point(value: Any, default: tuple[float, float] = (0.0, 0.0)) -> tuple[float, float]:
    if isinstance(value, (list, tuple)) and len(value) >= 2:
        return _num(value[0]), _num(value[1])
    return default


def _points(seq: Any) -> list[tuple[float, float]]:
    if not isinstance(seq, (list, tuple)):
        return []
    return [(_num(p[0]), _num(p[1]))
            for p in seq if isinstance(p, (list, tuple)) and len(p) >= 2]


def _bbox(pts: Iterable[tuple[float, float]]) -> tuple[float, float, float, float]:
    """(min_x, min_y, max_x, max_y) over a list of points."""
    pts = list(pts)
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    return min(xs), min(ys), max(xs), max(ys)


def _segments_to_d(segments: list) -> str:
    """Convert ``[["M", x, y], ["C", ...]]`` segment form to an SVG ``d`` string."""
    out: list[str] = []
    for seg in segments:
        if isinstance(seg, str):
            out.append(seg)
        elif isinstance(seg, (list, tuple)) and seg:
            cmd = str(seg[0])
            coords = " ".join(f"{_num(v):g}" for v in seg[1:])
            out.append(f"{cmd} {coords}".strip())
    return " ".join(out)


# --------------------------------------------------------------------------- #
# Layout engine -- returns child -> (x, y) relative to the group content box   #
# --------------------------------------------------------------------------- #


def layout_children(group: dict) -> dict[int, tuple[float, float]]:
    layout = group.get("layout") or {"kind": "free"}
    kind = layout.get("kind", "free")
    children = group.get("children") or []
    pt, pr, pb, pl = _pad(layout.get("padding"))
    gap = _num(layout.get("gap"), 0.0)
    row_gap = _num(layout.get("row_gap"), gap)
    col_gap = _num(layout.get("column_gap"), gap)
    align = layout.get("align") or "start"

    pos: dict[int, tuple[float, float]] = {}

    if kind == "free":
        for i, ch in enumerate(children):
            x, y, _, _ = _box(ch)
            pos[i] = (x, y)
        return pos

    if kind == "column":
        y = pt
        gx, gy, gw, gh = _box(group)
        inner_w = gw - pl - pr
        for i, ch in enumerate(children):
            w, h = _obj_size(ch)
            x = pl + _cross(align, inner_w, w)
            pos[i] = (x, y)
            y += h + gap
        return pos

    if kind == "row":
        x = pl
        gx, gy, gw, gh = _box(group)
        inner_h = gh - pt - pb
        for i, ch in enumerate(children):
            w, h = _obj_size(ch)
            y = pt + _cross(align, inner_h, h)
            pos[i] = (x, y)
            x += w + gap
        return pos

    if kind == "wrap":
        gx, gy, gw, gh = _box(group)
        inner_w = gw - pl - pr
        x, y, line_h = pl, pt, 0.0
        for i, ch in enumerate(children):
            w, h = _obj_size(ch)
            if x > pl and (x - pl) + w > inner_w:
                x = pl
                y += line_h + row_gap
                line_h = 0.0
            pos[i] = (x, y)
            x += w + col_gap
            line_h = max(line_h, h)
        return pos

    if kind == "grid":
        cols = int(layout.get("columns") or 1)
        sizes = [_obj_size(ch) for ch in children]
        n_rows = (len(children) + cols - 1) // cols
        col_w = [0.0] * cols
        row_h = [0.0] * n_rows
        for idx, (w, h) in enumerate(sizes):
            c, r = idx % cols, idx // cols
            col_w[c] = max(col_w[c], w)
            row_h[r] = max(row_h[r], h)
        x_off = [pl + sum(col_w[:c]) + c * col_gap for c in range(cols)]
        y_off = [pt + sum(row_h[:r]) + r * row_gap for r in range(n_rows)]
        for idx in range(len(children)):
            c, r = idx % cols, idx // cols
            pos[idx] = (x_off[c], y_off[r])
        return pos

    # unknown layout -> fall back to free
    for i, ch in enumerate(children):
        x, y, _, _ = _box(ch)
        pos[i] = (x, y)
    return pos


def _cross(align: str, extent: float, size: float) -> float:
    if align in ("center", "middle"):
        return (extent - size) / 2
    if align in ("end", "right", "bottom"):
        return extent - size
    return 0.0  # start / left / top / stretch


# --------------------------------------------------------------------------- #
# CSS builder                                                                  #
# --------------------------------------------------------------------------- #

_ALIGN_TO_TEXT = {"left": "left", "center": "center", "right": "right",
                  "justify": "justify", "start": "left", "end": "right"}
_VALIGN_TO_ITEMS = {"top": "flex-start", "middle": "center", "center": "center",
                    "bottom": "flex-end", "baseline": "baseline"}


def _flatten_inline_text(content: Any) -> str:
    """The plain text of an ``Inline`` list (``LinkInline.content`` and friends).

    Mirrors ``Renderer._flatten_span_text``: an inline is a bare string, a
    ``Span``/text-bearing dict, or a nested inline list.
    """
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, dict):
        if content.get("text") is not None:
            return str(content["text"])
        return _flatten_inline_text(content.get("content"))
    if isinstance(content, (list, tuple)):
        return "".join(_flatten_inline_text(c) for c in content)
    return str(content)


def text_style_css(style: dict, tokens: Tokens) -> dict[str, str]:
    """Translate a FrameForge text style (or inline Style) to CSS declarations."""
    css: dict[str, str] = {}
    fam = tokens.font_stack(style.get("font") or style.get("font_family"))
    if fam:
        css["font-family"] = fam
    size = style.get("size", style.get("font_size"))
    if size is not None:
        css["font-size"] = f"{_num(size)}px"
    weight = style.get("weight", style.get("font_weight"))
    if weight is not None:
        css["font-weight"] = str(weight)
    if style.get("italic"):
        css["font-style"] = "italic"
    color = tokens.color(style.get("color"))
    if color is not None:
        css["color"] = color
    lh = style.get("line_height")
    if lh is not None:
        css["line-height"] = str(lh) if isinstance(lh, (int, float)) else str(lh)
    ls = style.get("letter_spacing")
    if ls is not None:
        css["letter-spacing"] = f"{_num(ls)}px"
    # vertical alignment -> flex container cross axis
    valign = style.get("v_align") or style.get("vertical_align")
    css["align-items"] = _VALIGN_TO_ITEMS.get(valign, "flex-start")
    # horizontal alignment -> handled on the inner text node
    align = style.get("align") or style.get("text_align")
    css["--fg-text-align"] = _ALIGN_TO_TEXT.get(align, "left")
    # wrapping / clipping
    wrap = style.get("wrap")
    overflow = style.get("overflow")
    text_overflow = style.get("text_overflow")
    if wrap is False or overflow in ("clip", "hidden") or text_overflow == "clip":
        css["white-space"] = "nowrap"
        css["overflow"] = "hidden"
        if text_overflow:
            css["text-overflow"] = text_overflow
    else:
        css["white-space"] = "pre-wrap"
        css["overflow-wrap"] = "break-word"
    return css


def _decls(css: dict[str, str]) -> str:
    return "".join(f"{k}:{v};" for k, v in css.items())


def build_css(doc: dict, tokens: Tokens) -> str:
    parts: list[str] = []

    # ---- :root color variables (semantic palette) ----------------------- #
    if tokens.colors:
        root = "\n".join(
            f"  --fg-{_css_ident(name)}: {value};"
            for name, value in tokens.colors.items()
        )
        parts.append(f":root {{\n{root}\n}}")

    # ---- base / reset ---------------------------------------------------- #
    parts.append(
        """\
*,*::before,*::after{box-sizing:border-box;}
body{margin:0;background:#15161a;color:#e8eaed;
  font-family:'DejaVu Sans',Roboto,Arial,sans-serif;
  -webkit-font-smoothing:antialiased;padding:32px 16px;}
.sr-only{position:absolute;width:1px;height:1px;margin:-1px;padding:0;border:0;
  overflow:hidden;clip:rect(0,0,0,0);white-space:nowrap;}
.fg-doc{display:flex;flex-direction:column;align-items:center;gap:48px;}
.fg-figure{margin:0;display:flex;flex-direction:column;align-items:center;gap:14px;}
.fg-figcaption{max-width:480px;text-align:center;color:#9aa0a6;font-size:13px;
  line-height:1.5;}
.fg-figtitle{margin:0;font-size:15px;font-weight:600;color:#e8eaed;}
.fg-figmeta{display:block;margin-top:2px;}
.fg-figmeta code,.fg-figtitle code{color:inherit;}
.frameforge-page{position:relative;overflow:hidden;
  box-shadow:0 12px 40px rgba(0,0,0,.5);border-radius:4px;}
.fg-layer{position:absolute;inset:0;}
.fg-obj{position:absolute;box-sizing:border-box;}
.fg-text{display:flex;}
.fg-text>span{display:block;width:100%;text-align:var(--fg-text-align,left);}
/* Links inherit the authored colour — the document decides how a link looks,
   not the user agent; hover supplies the affordance. An `.fg-link` wrapping an
   object stays `position:static`, so the absolutely-positioned child still
   resolves against the page box and the geometry is unchanged.
   Selector shape matters: a rule whose RIGHTMOST compound carries a class must
   not also carry a type, a pseudo-class or a combinator, or it out-specifies a
   pooled class and `fg_css_optimize.risky_properties` has to keep those
   declarations inline (tests/test_fg_css_optimize.py). Hence `.fg-link` (bare
   class) and `a:hover` (bare type), never `a.fg-link:hover`. */
.fg-link{color:inherit;text-decoration:none;}
a:hover,a:focus-visible{text-decoration:underline;}
.fg-pagelinks{max-width:480px;font-size:13px;line-height:1.6;}
.fg-pagelinks ul{margin:0;padding:0;list-style:none;display:flex;flex-wrap:wrap;
  gap:6px 18px;justify-content:center;}
.fg-pagelinks a{color:#9aa0a6;text-decoration:underline;}
.fg-icon{display:flex;align-items:center;justify-content:center;
  line-height:1;text-align:center;}
.fg-image-placeholder{display:flex;align-items:center;justify-content:center;
  background:repeating-linear-gradient(45deg,#2a2b2d,#2a2b2d 6px,#303133 6px,#303133 12px);
  color:#9aa0a6;font-size:10px;text-align:center;overflow:hidden;}
.fg-line{overflow:visible;}
.fg-unknown{outline:1px dashed #c0392b;color:#c0392b;font-size:9px;
  display:flex;align-items:center;justify-content:center;}
.fg-flow-note{display:flex;align-items:center;justify-content:center;
  background:#1c1d21;outline:1px dashed #5a5f6a;}
.fg-flow-inner{max-width:60%;text-align:center;color:#9aa0a6;font-size:13px;
  line-height:1.6;}
.fg-flow-inner code{color:#e8eaed;}"""
    )

    # ---- one class per text style --------------------------------------- #
    for name, style in tokens.text_styles.items():
        css = text_style_css(style or {}, tokens)
        parts.append(f".fg-ts-{_css_ident(name)}{{{_decls(css)}}}")

    return "\n".join(parts)


# --------------------------------------------------------------------------- #
# HTML rendering of objects                                                    #
# --------------------------------------------------------------------------- #


def _is_gradient(fill: Any) -> bool:
    """True when a ``fill`` dict is a gradient (has stops / a gradient ``kind``)
    rather than a pattern."""
    return isinstance(fill, dict) and (
        bool(fill.get("stops")) or fill.get("kind") in ("linear", "radial", "conic")
    )


class Renderer:
    def __init__(self, tokens: Tokens, page_index: int = 0):
        self.tokens = tokens
        self._ids: set[str] = set()
        # Per-page counter for gradient <defs> ids. The page index prefixes each
        # id so gradients stay unique across pages sharing one HTML document.
        self._page_index = page_index
        self._gid = 0

    # -- id handling ------------------------------------------------------- #
    def dom_id(self, raw: Any) -> str | None:
        if raw is None:
            return None
        base = _css_ident(raw)
        ident, n = base, 2
        while ident in self._ids:
            ident = f"{base}-{n}"
            n += 1
        self._ids.add(ident)
        return ident

    # -- shared attributes ------------------------------------------------- #
    @staticmethod
    def _transform_css(ops: Any) -> str | None:
        """A CSS ``transform`` string from a model ``transform`` op list.

        CSS ``matrix(a,b,c,d,e,f)`` shares the model's affine convention, so the
        common ``matrix``/``translate`` ops map 1:1 (translate lets a group place
        its whole subtree — e.g. ``Mat3.translate`` onto a page)."""
        if not isinstance(ops, list):
            return None
        out: list[str] = []
        for op in ops:
            if not isinstance(op, dict):
                continue
            fn, args = op.get("fn"), (op.get("args") or [])
            if fn == "matrix" and len(args) == 6:
                out.append("matrix(" + ",".join(f"{_num(a):g}" for a in args) + ")")
            elif fn == "translate" and args:
                out.append("translate(" + ",".join(f"{_num(a):g}px" for a in args[:2]) + ")")
            elif fn == "scale" and args:
                out.append("scale(" + ",".join(f"{_num(a):g}" for a in args[:2]) + ")")
            elif fn == "rotate" and args:
                out.append(f"rotate({_num(args[0]):g}deg)")
            elif fn in ("skewX", "skewY") and args:
                out.append(f"{fn}({_num(args[0]):g}deg)")
        return " ".join(out) if out else None

    @staticmethod
    def _hex_rgb(color: Any) -> tuple[int, int, int] | None:
        """(r, g, b) from a ``#rgb``/``#rrggbb`` literal, else None (so tokens /
        named colours that cannot take an inline alpha are left untouched)."""
        if not isinstance(color, str) or not color.startswith("#"):
            return None
        c = color[1:]
        if len(c) == 3:
            c = "".join(ch * 2 for ch in c)
        if len(c) != 6:
            return None
        try:
            return int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16)
        except ValueError:
            return None

    @classmethod
    def _with_opacity(cls, color: str, op: Any) -> str:
        """Fold a ``fill_opacity`` into a hex colour as ``rgba(...)`` (so a tinted
        fill stays tinted rather than rendering solid and hiding overlaid text)."""
        if op is None:
            return color
        try:
            o = float(op)
        except (TypeError, ValueError):
            return color
        if o >= 1:
            return color
        rgb = cls._hex_rgb(color)
        if rgb is None:
            return color
        return f"rgba({rgb[0]},{rgb[1]},{rgb[2]},{o:g})"

    def _common(self, obj: dict, x: float, y: float, w: float, h: float,
                extra_classes: Iterable[str] = (), extra_css: dict | None = None,
                extra_attrs: dict | None = None):
        css = {
            "left": f"{x:.2f}px",
            "top": f"{y:.2f}px",
            "width": f"{w:.2f}px",
            "height": f"{h:.2f}px",
        }
        if obj.get("opacity") is not None:
            css["opacity"] = str(obj["opacity"])
        # A full `transform` op list (matrix/translate/scale/rotate/skew) wins and
        # is applied from the top-left origin to match the model's page-space
        # affine math; otherwise the `rotation` convenience field (centre origin).
        # `transform` is a CSS/Style property, so it rides in the `style` bag
        # (e.g. a group's `Mat3.translate(...)` placing its whole subtree); accept
        # a top-level one too for resilience.
        style = obj.get("style")
        tf_ops = obj.get("transform")
        if tf_ops is None and isinstance(style, dict):
            tf_ops = style.get("transform")
        tf = self._transform_css(tf_ops)
        if tf:
            css["transform"] = tf
            css["transform-origin"] = "0 0"
        else:
            rot = obj.get("rotation")
            if rot is not None:
                if isinstance(rot, dict):
                    ang = _num(rot.get("angle"))
                    css["transform"] = f"rotate({ang}deg)"
                else:
                    css["transform"] = f"rotate({_num(rot)}deg)"
        if extra_css:
            css.update(extra_css)
        classes = ["fg-obj", f"fg-{obj.get('type','obj')}", *extra_classes]
        attrs = [f'class="{" ".join(classes)}"']
        did = self.dom_id(obj.get("id"))
        if did:
            attrs.append(f'id="{did}"')
        if obj.get("id") is not None:
            attrs.append(f'data-fg-id="{html.escape(str(obj["id"]))}"')
        attrs.append(f'data-fg-type="{html.escape(str(obj.get("type","")))}"')
        if obj.get("bind"):
            attrs.append(f'data-bind="{html.escape(str(obj["bind"]))}"')
        # Accessibility (model-driven): a `decorative` object — and its whole
        # subtree — is hidden from assistive tech and any caller-supplied role
        # is dropped. Otherwise emit the caller's role / aria-* attributes.
        a11y = {"aria-hidden": "true"} if obj.get("decorative") else dict(extra_attrs or {})
        for name, val in a11y.items():
            attrs.append(f'{name}="{html.escape(str(val))}"')
        attrs.append(f'style="{_decls(css)}"')
        return " ".join(attrs)

    def _border(self, obj: dict) -> str | None:
        """Resolve stroke / stroke_style into a CSS border shorthand."""
        ss = obj.get("stroke_style")
        stroke, width = None, None
        if isinstance(ss, str):
            spec = self.tokens.stroke_styles.get(ss, {})
            stroke = self.tokens.color(spec.get("stroke"))
            width = spec.get("stroke_width")
        elif isinstance(ss, dict):
            stroke = self.tokens.color(ss.get("stroke"))
            width = ss.get("stroke_width")
        if obj.get("stroke") is not None:
            stroke = self.tokens.color(obj.get("stroke"))
        if stroke is None:
            return None
        return f"{_num(width, 1.0)}px solid {stroke}"

    def _stroke_literal(self, obj: dict) -> tuple[str | None, float]:
        """Stroke color + width as raw values (for SVG)."""
        ss = obj.get("stroke_style")
        stroke, width = None, 1.0
        if isinstance(ss, str):
            spec = self.tokens.stroke_styles.get(ss, {})
            stroke = self.tokens.color_literal(spec.get("stroke"))
            width = _num(spec.get("stroke_width"), 1.0)
        elif isinstance(ss, dict):
            stroke = self.tokens.color_literal(ss.get("stroke"))
            width = _num(ss.get("stroke_width"), 1.0)
        if obj.get("stroke") is not None:
            stroke = self.tokens.color_literal(obj.get("stroke"))
        return stroke, width

    def _paint_css(self, obj: dict, *, fillable: bool,
                   origin: tuple[float, float] = (0.0, 0.0)) -> tuple[str, str]:
        """CSS ``fill``/``stroke`` for an inline SVG shape, plus any ``<defs>``.

        Returns ``(style, defs)``. Solid colours keep the semantic palette
        (``var(--fg-name)``); a **gradient** ``fill`` is emitted as a real SVG
        ``<linearGradient>``/``<radialGradient>`` referenced by ``fill:url(#id)``
        (the ``defs`` string the caller injects into the shape's ``<svg>``).
        ``origin`` is the shape's svg-local origin in object coordinates —
        A1 user-space gradient geometry shifts by ``-origin`` into the rebased
        viewBox. A non-gradient dict (a pattern) still degrades to a flat colour
        rather than vanishing.
        """
        decls: list[str] = []
        defs = ""
        fill = obj.get("fill")
        if fillable and isinstance(fill, dict):
            if _is_gradient(fill):
                gid, defs = self._gradient_svg(fill, origin)
                decls.append(f"fill:url(#{gid})")
            else:
                decls.append("fill:#888888")      # pattern — not yet supported
        elif fillable and fill is not None:
            decls.append(f"fill:{self.tokens.color(fill)}")
            fo = obj.get("fill_opacity")
            if fo is not None:
                decls.append(f"fill-opacity:{_num(fo, 1.0):g}")
        else:
            decls.append("fill:none")
        # stroke: stroke_style (token bundle or inline), overridden by `stroke`
        ss = obj.get("stroke_style")
        stroke, width = None, None
        if isinstance(ss, str):
            spec = self.tokens.stroke_styles.get(ss, {})
            stroke, width = spec.get("stroke"), spec.get("stroke_width")
        elif isinstance(ss, dict):
            stroke, width = ss.get("stroke"), ss.get("stroke_width")
        if obj.get("stroke") is not None:
            stroke = obj.get("stroke")
        if stroke is not None:
            decls.append(f"stroke:{self.tokens.color(stroke)}")
            decls.append(f"stroke-width:{_num(width, 1.0):g}")
            decls.append("stroke-linejoin:round")
            decls.append("stroke-linecap:round")
        return ";".join(decls), defs

    # -- gradients --------------------------------------------------------- #
    @staticmethod
    def _user_point(value: Any) -> "tuple[float, float] | None":
        """A numeric [x, y] pair to (x, y) floats, else None (A1 guard)."""
        if (isinstance(value, (list, tuple)) and len(value) == 2
                and all(isinstance(v, (int, float)) and not isinstance(v, bool)
                        for v in value)):
            return float(value[0]), float(value[1])
        return None

    @classmethod
    def _user_line(cls, g: dict) -> "tuple[tuple[float, float], tuple[float, float]] | None":
        """The A1 `line` [[x1,y1],[x2,y2]] as two float points, else None."""
        line = g.get("line")
        if isinstance(line, (list, tuple)) and len(line) == 2:
            p0, p1 = cls._user_point(line[0]), cls._user_point(line[1])
            if p0 is not None and p1 is not None:
                return p0, p1
        return None

    @classmethod
    def _user_radial(cls, g: dict) -> "tuple[float, float, float] | None":
        """The A1 user-space radial (cx, cy, r), else None."""
        r = g.get("radius")
        centre = cls._user_point(g.get("at"))
        if (centre is not None and isinstance(r, (int, float))
                and not isinstance(r, bool) and r > 0 and g.get("kind") == "radial"):
            return centre[0], centre[1], float(r)
        return None

    def _gradient_stops(self, g: dict) -> list[tuple[float, str, "float | None"]]:
        """`[(offset_percent, color_literal, opacity|None)]` from a gradient dict.

        Mirrors the SVG painter's stop parsing: a ``position`` may be a bare
        number (already a percentage) or a ``"NN%"`` string; missing positions
        space evenly. ``opacity`` is the A1 per-stop alpha (0..1) or None."""
        stops = g.get("stops") or []
        n = max(1, len(stops))
        out: list[tuple[float, str, float | None]] = []
        for i, st in enumerate(stops):
            off = st.get("position")
            o: float | None = None
            if isinstance(off, (int, float)):
                o = float(off)
            elif isinstance(off, str) and off.strip().endswith("%"):
                try:
                    o = float(off.strip()[:-1])
                except ValueError:
                    o = None
            if o is None:
                o = (i / (n - 1) * 100) if n > 1 else 0.0
            col = self.tokens.color_literal(st.get("color")) or "#000000"
            op = st.get("opacity")
            alpha = (float(op) if isinstance(op, (int, float))
                     and not isinstance(op, bool) else None)
            out.append((o, col, alpha))
        return out

    @staticmethod
    def _gradient_center(g: dict) -> tuple[str, str]:
        at = g.get("at")
        if isinstance(at, str) and len(at.split()) == 2:
            cx, cy = at.split()
            return cx, cy
        return "50%", "50%"

    @staticmethod
    def _gradient_angle(g: dict) -> float | None:
        a = g.get("angle")
        try:
            return float(a) if a is not None else None
        except (TypeError, ValueError):
            return None

    def _gradient_svg(self, g: dict, origin: tuple[float, float] = (0.0, 0.0)) -> tuple[str, str]:
        """Allocate a page-unique id and build the SVG ``<defs>`` for a gradient.

        Returns ``(gid, defs_markup)``. ``origin`` is the emitting shape's
        svg-local origin in object coordinates: A1 user-space geometry (`line`,
        `at`+`radius`+`focal`) is authored in the object's coordinate space and
        shifted by ``-origin`` into the shape's rebased viewBox. Conic gradients
        (no SVG primitive) fall back to radial, as the SVG painter does."""
        self._gid += 1
        gid = f"fgg-{self._page_index}-{self._gid}"
        stops = "".join(
            f'<stop offset="{o:g}%" stop-color="{html.escape(c)}"'
            + (f' stop-opacity="{a:g}"' if a is not None else "") + "/>"
            for o, c, a in self._gradient_stops(g)
        )
        gx, gy = origin
        if g.get("kind") in ("radial", "conic"):
            user = self._user_radial(g)
            if user is not None:
                ucx, ucy, r = user
                focal = self._user_point(g.get("focal"))
                fx, fy = focal if focal is not None else (ucx, ucy)
                defs = (f'<defs><radialGradient id="{gid}" gradientUnits="userSpaceOnUse" '
                        f'cx="{ucx - gx:g}" cy="{ucy - gy:g}" r="{r:g}" '
                        f'fx="{fx - gx:g}" fy="{fy - gy:g}">{stops}</radialGradient></defs>')
            else:
                cx, cy = self._gradient_center(g)
                defs = (f'<defs><radialGradient id="{gid}" cx="{html.escape(cx)}" '
                        f'cy="{html.escape(cy)}" r="50%">{stops}</radialGradient></defs>')
        else:
            line = self._user_line(g)
            if line is not None:
                (x1, y1), (x2, y2) = line
                defs = (f'<defs><linearGradient id="{gid}" gradientUnits="userSpaceOnUse" '
                        f'x1="{x1 - gx:g}" y1="{y1 - gy:g}" '
                        f'x2="{x2 - gx:g}" y2="{y2 - gy:g}">{stops}</linearGradient></defs>')
            else:
                deg = self._gradient_angle(g)
                xform = f' gradientTransform="rotate({deg:g} 0.5 0.5)"' if deg is not None else ""
                defs = f'<defs><linearGradient id="{gid}"{xform}>{stops}</linearGradient></defs>'
        return gid, defs

    def _css_stop(self, color: str, alpha: "float | None") -> str:
        """One CSS gradient stop colour, folding an A1 stop opacity to rgba()."""
        return self._with_opacity(color, alpha) if alpha is not None else color

    def _gradient_css(self, g: dict, origin: tuple[float, float] = (0.0, 0.0)) -> str:
        """A CSS ``linear-gradient()``/``radial-gradient()`` for a div background.

        A1 user-space geometry degrades honestly in this lane: a radial
        ``at``+``radius`` IS expressible (CSS radial-gradient speaks px —
        shifted by ``-origin`` from object into div coordinates); a linear
        ``line`` keeps its DIRECTION as the equivalent CSS angle (the extent
        would need a per-box stop projection CSS cannot state)."""
        parts = ", ".join(
            f"{self._css_stop(c, a)} {o:g}%" for o, c, a in self._gradient_stops(g))
        if g.get("kind") in ("radial", "conic"):
            user = self._user_radial(g)
            if user is not None:
                ucx, ucy, r = user
                gx, gy = origin
                return (f"radial-gradient(circle {r:g}px at "
                        f"{ucx - gx:g}px {ucy - gy:g}px, {parts})")
            cx, cy = self._gradient_center(g)
            shape = "circle" if g.get("shape") == "circle" else "ellipse"
            return f"radial-gradient({shape} at {cx} {cy}, {parts})"
        line = self._user_line(g)
        if line is not None:
            (x1, y1), (x2, y2) = line
            dx, dy = x2 - x1, y2 - y1
            if dx or dy:
                deg = math.degrees(math.atan2(dx, -dy)) % 360.0
                return f"linear-gradient({deg:g}deg, {parts})"
        deg = self._gradient_angle(g)
        head = f"{deg:g}deg" if deg is not None else "to bottom"
        return f"linear-gradient({head}, {parts})"

    # -- dispatch ---------------------------------------------------------- #
    def render(self, obj: dict, ox: float, oy: float) -> str:
        """Render one object. (ox, oy) is the origin of the positioning context."""
        t = obj.get("type")
        method = getattr(self, f"_render_{t}", None)
        markup = (self._render_unknown(obj, ox, oy) if method is None
                  else method(obj, ox, oy))
        # An object-level `href` wraps its markup in a real anchor — parity with
        # the SVG painter, which has always done this (tests/test_link_render.py).
        # Without it an exported page had zero clickable elements (GH P1-3).
        href = obj.get("href")
        if href:
            markup = (f'<a class="fg-link" '
                      f'href="{html.escape(str(href), quote=True)}">{markup}</a>')
        return markup

    def _render_rect(self, obj, ox, oy):
        x, y, w, h = _box(obj)
        css = {}
        raw = obj.get("fill")
        if _is_gradient(raw):
            css["background"] = self._gradient_css(raw, origin=(x, y))
        elif not isinstance(raw, dict) and (fill := self.tokens.color(raw)) is not None:
            css["background"] = self._with_opacity(fill, obj.get("fill_opacity"))
        radius = obj.get("radius")
        if radius is not None:
            css["border-radius"] = f"{_num(radius)}px"
        border = self._border(obj)
        if border:
            css["border"] = border
        return f"<div {self._common(obj, ox + x, oy + y, w, h, extra_css=css)}></div>"

    def _render_text(self, obj, ox, oy):
        x, y, w, h = _box(obj)
        classes, css = [], {}
        style = obj.get("style")
        if isinstance(style, str):
            classes.append(f"fg-ts-{_css_ident(style)}")
        elif isinstance(style, dict):
            css.update(text_style_css(style, self.tokens))
        text = obj.get("text")
        if text is None and obj.get("spans"):
            # Emit ONE run per authored span, each carrying its own declarations.
            # Flattening spans to a plain string silently dropped every per-span
            # style — the brand wordmark and `fan()` labels are authored as
            # coloured runs, so they inherited the document body colour and
            # vanished on a light ground, while SVG rendered them correctly.
            #
            # The runs nest inside a single wrapper <span>, because the sheet's
            # `.fg-text>span` rule makes a *direct* child a block: sibling runs
            # would stack vertically instead of flowing on one line.
            body = "".join(self._render_span(s) for s in obj["spans"])
        else:
            body = html.escape(text or "")
        attrs = self._common(obj, ox + x, oy + y, w, h,
                             extra_classes=classes, extra_css=css)
        return f"<div {attrs}><span>{body}</span></div>"

    def _render_span(self, span: Any) -> str:
        """One inline run: its text, plus whatever style that run declared.

        A ``{"kind": "link"}`` run (``LinkInline``) becomes a real ``<a href>``
        around its flattened content — the SVG painter has always done this, so
        without it the same document exported to HTML had inert text where the
        author wrote a link (GH P1-3). A link with no ``href`` degrades to plain
        text rather than emitting an anchor with nothing to point at.
        """
        if not isinstance(span, dict):
            return html.escape(str(span))
        if span.get("kind") == "link":
            inner = html.escape(_flatten_inline_text(span.get("content")))
            href = span.get("href")
            if not href:
                return inner
            title = span.get("title")
            attrs = f' title="{html.escape(str(title), quote=True)}"' if title else ""
            return (f'<a class="fg-link" href="{html.escape(str(href), quote=True)}"'
                    f"{attrs}>{inner}</a>")
        run = html.escape(str(span.get("text", "")))
        style = span.get("style")
        if not isinstance(style, dict):
            return run
        css = text_style_css(style, self.tokens)
        # `text-align` is a block property; a nested inline run cannot honour it
        # and the wrapper already carries the object's alignment.
        css.pop("--fg-text-align", None)
        css.pop("text-align", None)
        if not css:
            return run
        decl = "".join(f"{k}:{v};" for k, v in css.items())
        return f'<span style="{html.escape(decl, quote=True)}">{run}</span>'

    def _render_icon(self, obj, ox, oy):
        x, y, w, h = _box(obj)
        size = obj.get("size") or min(w, h) or 16
        css = {
            "font-size": f"{_num(size)}px",
            "color": self.tokens.color(obj.get("color")) or "currentColor",
        }
        fam = self.tokens.font_stack(obj.get("font"))
        if fam:
            css["font-family"] = fam
        glyph_name = obj.get("glyph", "")
        glyph = html.escape(self.tokens.glyph(glyph_name))
        label = _icon_label(glyph_name)
        a11y = {"role": "img", "aria-label": label} if label else {"aria-hidden": "true"}
        attrs = self._common(obj, ox + x, oy + y, w, h, extra_css=css, extra_attrs=a11y)
        return f"<div {attrs}>{glyph}</div>"

    def _render_ellipse(self, obj, ox, oy):
        cx, cy = (_num(c) for c in (obj.get("center") or [0, 0]))
        rx, ry = _num(obj.get("rx")), _num(obj.get("ry"))
        x, y, w, h = cx - rx, cy - ry, 2 * rx, 2 * ry
        css = {"border-radius": "50%"}
        raw = obj.get("fill")
        if _is_gradient(raw):
            css["background"] = self._gradient_css(raw, origin=(x, y))
        elif not isinstance(raw, dict) and (fill := self.tokens.color(raw)) is not None:
            css["background"] = self._with_opacity(fill, obj.get("fill_opacity"))
        border = self._border(obj)
        if border:
            css["border"] = border
        return f"<div {self._common(obj, ox + x, oy + y, w, h, extra_css=css)}></div>"

    def _render_line(self, obj, ox, oy):
        (x1, y1), (x2, y2) = _line_points(obj)
        stroke, width = self._stroke_literal(obj)
        stroke = stroke or "currentColor"
        pad = max(width, 1.0)
        minx, miny = min(x1, x2) - pad, min(y1, y2) - pad
        bw, bh = abs(x2 - x1) + 2 * pad, abs(y2 - y1) + 2 * pad
        lx1, ly1, lx2, ly2 = x1 - minx, y1 - miny, x2 - minx, y2 - miny
        attrs = self._common(obj, ox + minx, oy + miny, bw, bh)
        svg = (
            f'<svg aria-hidden="true" width="{bw:.2f}" height="{bh:.2f}" '
            f'viewBox="0 0 {bw:.2f} {bh:.2f}" '
            f'style="position:absolute;inset:0;overflow:visible">'
            f'<line x1="{lx1:.2f}" y1="{ly1:.2f}" x2="{lx2:.2f}" y2="{ly2:.2f}" '
            f'stroke="{stroke}" stroke-width="{width}" stroke-linecap="round"/></svg>'
        )
        return f"<div {attrs}>{svg}</div>"

    def _svg_poly(self, obj, ox, oy, pts, *, closed: bool) -> str:
        """Shared renderer for polyline/polygon: a tight SVG box + one element."""
        if len(pts) < 2:
            return self._render_unknown(obj, ox, oy)
        _, sw = self._stroke_literal(obj)
        pad = max(sw, 1.0)
        minx, miny, maxx, maxy = _bbox(pts)
        bw, bh = (maxx - minx) + 2 * pad, (maxy - miny) + 2 * pad
        local = " ".join(f"{x - minx + pad:.2f},{y - miny + pad:.2f}" for x, y in pts)
        tag = "polygon" if closed else "polyline"
        paint, defs = self._paint_css(obj, fillable=True, origin=(minx - pad, miny - pad))
        attrs = self._common(obj, ox + minx - pad, oy + miny - pad, bw, bh)
        svg = (
            f'<svg aria-hidden="true" width="{bw:.2f}" height="{bh:.2f}" '
            f'viewBox="0 0 {bw:.2f} {bh:.2f}" '
            f'style="position:absolute;inset:0;overflow:visible">'
            f'{defs}<{tag} points="{local}" style="{html.escape(paint)}"/></svg>'
        )
        return f"<div {attrs}>{svg}</div>"

    def _render_polyline(self, obj, ox, oy):
        return self._svg_poly(obj, ox, oy, _points(obj.get("points")),
                              closed=bool(obj.get("closed")))

    def _render_polygon(self, obj, ox, oy):
        return self._svg_poly(obj, ox, oy, _points(obj.get("points")), closed=True)

    def _render_circle(self, obj, ox, oy):
        # A circle is an ellipse with rx == ry == r; reuse the ellipse renderer.
        r = obj.get("r")
        return self._render_ellipse({**obj, "rx": r, "ry": r}, ox, oy)

    def _render_curve(self, obj, ox, oy):
        p0 = _point(obj.get("from"))
        p3 = _point(obj.get("to"))
        c1 = _point(obj.get("control1") or obj.get("c1") or obj.get("from"))
        c2 = _point(obj.get("control2") or obj.get("c2") or obj.get("to"))
        _, sw = self._stroke_literal(obj)
        pad = max(sw, 1.0)
        minx, miny, maxx, maxy = _bbox([p0, p3, c1, c2])
        bw, bh = (maxx - minx) + 2 * pad, (maxy - miny) + 2 * pad

        def loc(p):
            return p[0] - minx + pad, p[1] - miny + pad

        (ax, ay), (bx, by), (cx_, cy_), (dx, dy) = loc(p0), loc(c1), loc(c2), loc(p3)
        d = f"M {ax:.2f} {ay:.2f} C {bx:.2f} {by:.2f} {cx_:.2f} {cy_:.2f} {dx:.2f} {dy:.2f}"
        paint, defs = self._paint_css(obj, fillable=obj.get("fill") is not None,
                                      origin=(minx - pad, miny - pad))
        attrs = self._common(obj, ox + minx - pad, oy + miny - pad, bw, bh)
        svg = (
            f'<svg aria-hidden="true" width="{bw:.2f}" height="{bh:.2f}" '
            f'viewBox="0 0 {bw:.2f} {bh:.2f}" '
            f'style="position:absolute;inset:0;overflow:visible">'
            f'{defs}<path d="{d}" style="{html.escape(paint)}"/></svg>'
        )
        return f"<div {attrs}>{svg}</div>"

    # Curve is exposed under two type names in the model (`curve` | `bezier`).
    _render_bezier = _render_curve

    def _render_path(self, obj, ox, oy):
        d = obj.get("d")
        if isinstance(d, list):
            d = _segments_to_d(d)
        if not isinstance(d, str) or not d.strip():
            return self._render_unknown(obj, ox, oy)
        # A `d` string can carry relative commands and arcs, so a generic tight
        # bbox/translate is unsafe. Anchor an overflow-visible SVG at the
        # positioning origin and paint the path in its authored coordinates.
        paint, defs = self._paint_css(obj, fillable=obj.get("fill") is not None)
        attrs = self._common(obj, ox, oy, 0, 0, extra_css={"overflow": "visible"})
        svg = (
            f'<svg aria-hidden="true" width="1" height="1" overflow="visible" '
            f'style="position:absolute;overflow:visible">'
            f'{defs}<path d="{html.escape(d)}" style="{html.escape(paint)}"/></svg>'
        )
        return f"<div {attrs}>{svg}</div>"

    def _render_image(self, obj, ox, oy):
        x, y, w, h = _box(obj)
        css = {}
        clip = obj.get("clip")
        shape = clip.get("shape") if isinstance(clip, dict) else (
            "ellipse" if clip in ("ellipse", "circle") else None
        )
        if shape in ("ellipse", "circle"):
            css["border-radius"] = "50%"
            css["overflow"] = "hidden"
        elif obj.get("radius") is not None:
            css["border-radius"] = f"{_num(obj['radius'])}px"
        src = obj.get("src", "")
        usable = (not obj.get("placeholder")) and (
            src.startswith(("http://", "https://", "data:")) or os.path.exists(src)
        )
        if usable:
            css["object-fit"] = "cover"
            attrs = self._common(obj, ox + x, oy + y, w, h, extra_css=css)
            # A decorative image gets an empty alt (and `_common` adds aria-hidden);
            # otherwise prefer alt, then the PDF/UA actual_text fallback.
            alt = "" if obj.get("decorative") else html.escape(
                obj.get("alt") or obj.get("actual_text") or "")
            return f'<img {attrs} src="{html.escape(src)}" alt="{alt}">'
        label_text = obj.get("label") or obj.get("alt") or os.path.basename(src) or "image"
        a11y = None if obj.get("decorative") else {"role": "img", "aria-label": label_text}
        attrs = self._common(obj, ox + x, oy + y, w, h,
                             extra_classes=["fg-image-placeholder"], extra_css=css,
                             extra_attrs=a11y)
        return f"<div {attrs}>{html.escape(label_text)}</div>"

    def _render_unknown(self, obj, ox, oy):
        """Fallback for object types this renderer does not implement."""
        x, y, w, h = _box(obj)
        if w == 0 and h == 0:
            w, h = 80, 24  # give it a visible footprint
        label = html.escape(str(obj.get("type", "?")))
        attrs = self._common(obj, ox + x, oy + y, w, h,
                             extra_classes=["fg-unknown"])
        return f'<div {attrs} title="unsupported type">{label}</div>'

    def _render_group(self, obj, ox, oy):
        gx, gy, gw, gh = _box(obj)
        attrs = self._common(obj, ox + gx, oy + gy, gw, gh, extra_attrs={"role": "group"})
        children = obj.get("children") or []
        positions = layout_children(obj)
        inner = []
        for i, child in enumerate(children):
            cx, cy = positions.get(i, (0.0, 0.0))
            # children are positioned relative to the group box -> origin (0,0)
            # but their own (cx, cy) offset within it.
            inner.append(self._render_child(child, cx, cy))
        return f"<div {attrs}>\n{''.join(inner)}\n</div>"

    def _render_child(self, obj, cx, cy):
        """
        Render a child inside a group. ``(cx, cy)`` is the child's offset within
        the group content box. Shape-anchored types (ellipse/line) carry their
        own coordinates, so we translate the positioning context instead of the
        box: pass (cx - box.x, cy - box.y) so ``box``/``center``/``from`` end up
        at (cx, cy).
        """
        t = obj.get("type")
        if t in ("ellipse", "circle", "line", "polyline", "polygon", "path",
                 "curve", "bezier"):
            # These carry their own coords (center / from / to / points / d)
            # rather than a box. In a free group the computed offset is (0,0),
            # so the coords are used as-is; in an auto-layout group (cx, cy)
            # shifts them.
            return self.render(obj, cx, cy)
        bx, by, _, _ = _box(obj)
        # Box-based child: translate the context so its box lands at (cx, cy).
        return self.render(obj, cx - bx, cy - by)


# --------------------------------------------------------------------------- #
# Page / document assembly                                                      #
# --------------------------------------------------------------------------- #


# Canvas resolution is shared with the canonical render path — the HTML backend
# delegates to the ONE implementation (`CanvasResolver`, aliased at the top of
# this module) rather than mirroring it, so preset sizes, `orientation`, and
# physical `units` can never diverge between `--to svg`/`pdf-tex` and
# `--to html`; the default likewise comes from the canonical `DEFAULT_WH`
# (drift-risk-map #4, Track B handoff). This lane renders pages standalone
# (no master canvas inheritance, as before), hence the empty masters map.
_PAGE_CANVAS = _CanvasResolver({})


def canvas_size(page: dict, default=_HTML_DEFAULT_WH) -> tuple[float, float]:
    """Resolve a page's canvas to (w, h): inline size (units-aware), named
    preset (orientation-aware), or default — via the canonical CanvasResolver."""
    if page.get("canvas") is None:
        return default
    return _PAGE_CANVAS.resolve(page)


def page_link_href(link: dict) -> str:
    """The href for one ``PageLink``: an external URL, or a same-document anchor.

    Internal targets point at the page box's own ``id`` (``page-<id>``) rather
    than a second, parallel anchor scheme — one id per page, so the link always
    has something real to jump to.
    """
    to = str(link.get("to", ""))
    if link.get("external") or re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*:|^//|^#", to):
        return to
    return f"#page-{_css_ident(to)}"


def render_page_links(page: dict) -> str:
    """``Page.links`` as a real navigation landmark.

    ``PageLink`` has been in the model since 2.0 but no backend rendered it, so
    authored navigation vanished on export (GH P1-3). It is emitted OUTSIDE the
    fixed-size canvas box: the page is an absolutely-positioned coordinate
    space, and injecting flow content into it would overlay the artwork.
    """
    links = page.get("links") or []
    if not links:
        return ""
    items = []
    for link in links:
        if not isinstance(link, dict) or not link.get("to"):
            continue
        href = page_link_href(link)
        label = html.escape(str(link.get("label") or link.get("to")))
        rel = link.get("relation")
        rel_attr = f' rel="{html.escape(str(rel), quote=True)}"' if rel else ""
        ext = ' target="_blank"' if link.get("external") else ""
        items.append(
            f'<li><a class="fg-link" href="{html.escape(href, quote=True)}"'
            f"{rel_attr}{ext}>{label}</a></li>"
        )
    if not items:
        return ""
    return ('<nav class="fg-pagelinks" aria-label="Page links">\n'
            f"<ul>{''.join(items)}</ul>\n</nav>")


def render_page(page: dict, tokens: Tokens, index: int) -> str:
    renderer = Renderer(tokens, page_index=index)
    w, h = canvas_size(page)
    layers = sorted(
        (page.get("layers") or []),
        key=lambda L: _num(L.get("z"), 0),
    )
    layer_html: list[str] = []
    for layer in layers:
        z = _num(layer.get("z"), 0)
        lid = _css_ident(layer.get("id", f"layer{index}"))
        objects = layer.get("objects") or []
        body = "\n".join(renderer.render(o, 0.0, 0.0) for o in objects)
        op = layer.get("opacity")
        op_css = f"opacity:{op};" if op is not None else ""
        layer_html.append(
            f'<section class="fg-layer" id="layer-{lid}" '
            f'data-layer="{html.escape(str(layer.get("id","")))}" '
            f'data-z="{z:g}" style="z-index:{int(z)};{op_css}">\n'
            f"{body}\n</section>"
        )

    page_id = html.escape(str(page.get("id", f"page-{index}")))
    return (
        f'<div class="frameforge-page" id="page-{_css_ident(page.get("id", index))}" '
        f'data-page-id="{page_id}" '
        f'style="width:{w:g}px;height:{h:g}px;">\n'
        + "\n".join(layer_html)
        + "\n</div>"
    )


def render_flow_placeholder(section: dict, w: float, h: float) -> str:
    """Visible placeholder for a ``mode: flow`` section (document/flow profile).

    This renderer only handles the diagram/canvas profile. A flow section has a
    ``story`` of flowables and no ``layers``; rather than silently emit an empty
    page, surface a labelled note — consistent with how unknown *objects* are
    shown rather than dropped.
    """
    sid = html.escape(str(section.get("id", "")))
    n = len(section.get("story") or [])
    return (
        f'<div class="frameforge-page fg-flow-note" '
        f'style="width:{w:g}px;height:{h:g}px;">'
        f'<div class="fg-flow-inner">flow section <code>{sid}</code>'
        f"<br>{n} flowable(s) &middot; document/flow profile not rendered "
        f"by this tool</div></div>"
    )


def render_document(doc: dict) -> str:
    tokens = Tokens(doc)
    css = build_css(doc, tokens)
    pages = doc.get("pages") or []

    blocks: list[str] = []
    for i, page in enumerate(pages):
        title = page.get("title") or doc.get("title") or ""
        w, h = canvas_size(page)
        if page.get("mode") == "flow":
            page_html = render_flow_placeholder(page, *(w, h))
        else:
            page_html = render_page(page, tokens, i)
        cap_id = f"fg-figcap-{i}"
        page_id_html = html.escape(str(page.get("id", "")))
        if title:
            head = f'<h2 class="fg-figtitle" id="{cap_id}">{html.escape(str(title))}</h2>'
            meta = (f'<span class="fg-figmeta">page <code>{page_id_html}</code> '
                    f"&middot; {w:g}&times;{h:g}px</span>")
        else:
            head = (f'<span class="fg-figtitle" id="{cap_id}">page '
                    f"<code>{page_id_html}</code></span>")
            meta = f'<span class="fg-figmeta">{w:g}&times;{h:g}px</span>'
        figcaption = f'<figcaption class="fg-figcaption">{head}{meta}</figcaption>'
        nav = render_page_links(page)
        if nav:
            page_html = f"{page_html}\n{nav}"
        # <figure>/<figcaption> associate the caption with the artifact, and
        # aria-labelledby gives the figure its accessible name.
        blocks.append(
            f'<figure class="fg-figure" role="group" aria-labelledby="{cap_id}">\n'
            f"{figcaption}\n{page_html}\n</figure>"
        )

    doc_title = html.escape(str(doc.get("title") or "FrameForge render"))
    description = html.escape(str(doc.get("description") or ""))
    lang = html.escape(str(doc.get("lang") or "en"))

    return f"""<!DOCTYPE html>
<html lang="{lang}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="generator" content="frameforge (html backend)">
<meta name="description" content="{description}">
<title>{doc_title}</title>
<style>
{css}
</style>
</head>
<body>
<main class="fg-doc">
<h1 class="sr-only">{doc_title}</h1>
{chr(10).join(blocks)}
</main>
</body>
</html>
"""


# --------------------------------------------------------------------------- #
# DocumentRenderer port adapter                                                #
# --------------------------------------------------------------------------- #


class HtmlDocumentRenderer:
    """HTML/CSS output backend — the `DocumentRenderer` port, in-process.

    A thin adapter over the pure `render_document` transform above. This module
    used to be `tooling/frameforge_to_html.py`, reached by the CLI through a
    subprocess; it now lives in the package and is reached through the port, so
    no caller shells out to our own script to render HTML.
    """

    target = "html"
    kind = "web"
    blurb = "HTML/CSS (semantic; flow-mode limits)"

    def available(self) -> "str | None":
        return None  # pure Python — no optional dependency, no external binary

    def render(self, document, *, base_dir=None, options=None) -> RenderedArtifact:
        # `base_dir`/`options` are unused: HTML embeds asset hrefs verbatim and
        # takes no per-invocation knobs. They are accepted to satisfy the port.
        return RenderedArtifact(
            pages=[render_document(document)],
            media_type="text/html",
            extension="html",
            one_file_per_page=False,
        )
