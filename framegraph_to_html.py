#!/usr/bin/env python3
"""
framegraph_to_html.py
=====================

Rebuild an HTML page from a FrameGraph v2 document (the `diagram` profile:
canvas + layers + absolutely-positioned objects).

The output is *layered* and *semantically named*:

  * each page is a ``<figure>`` carrying a ``<figcaption>`` that labels it
  * one ``<section class="fg-layer" data-layer="...">`` per layer, stacked by ``z``
  * ``group`` objects become nested ``<div class="fg-group" role="group">``
  * every object keeps its FrameGraph ``id`` as the DOM ``id``
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
emitted as labelled placeholders — never silently dropped. ``fill`` paints
that are gradients/patterns degrade to a flat colour on SVG shapes.

Usage
-----
    python framegraph_to_html.py input.yaml [-o output.html]
    python framegraph_to_html.py input.json --schema framegraph-v2_schema.json --validate

YAML input needs PyYAML; JSON input needs nothing extra. ``--validate``
needs ``jsonschema`` (optional; skipped with a notice if absent).
"""

from __future__ import annotations

import argparse
import html
import json
import os
import re
import sys
from typing import Any, Iterable

# --------------------------------------------------------------------------- #
# Loading                                                                      #
# --------------------------------------------------------------------------- #


def load_document(path: str) -> dict:
    """Load a FrameGraph document from YAML or JSON."""
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
        # (models/framegraph.py Tokens). Merge both so a `style:` name reference
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


def text_style_css(style: dict, tokens: Tokens) -> dict[str, str]:
    """Translate a FrameGraph text style (or inline Style) to CSS declarations."""
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
.framegraph-page{position:relative;overflow:hidden;
  box-shadow:0 12px 40px rgba(0,0,0,.5);border-radius:4px;}
.fg-layer{position:absolute;inset:0;}
.fg-obj{position:absolute;box-sizing:border-box;}
.fg-text{display:flex;}
.fg-text>span{display:block;width:100%;text-align:var(--fg-text-align,left);}
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


class Renderer:
    def __init__(self, tokens: Tokens):
        self.tokens = tokens
        self._ids: set[str] = set()

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

    def _paint_css(self, obj: dict, *, fillable: bool) -> str:
        """CSS ``fill``/``stroke`` declarations for an inline SVG shape.

        Solid colours keep the semantic palette (``var(--fg-name)``); a
        gradient/pattern ``fill`` (a dict) is not expressible as a single SVG
        paint, so it degrades to a flat colour rather than vanishing.
        """
        decls: list[str] = []
        fill = obj.get("fill")
        if fillable and isinstance(fill, dict):
            decls.append("fill:#888888")          # gradient/pattern not supported
        elif fillable and fill is not None:
            decls.append(f"fill:{self.tokens.color(fill)}")
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
        return ";".join(decls)

    # -- dispatch ---------------------------------------------------------- #
    def render(self, obj: dict, ox: float, oy: float) -> str:
        """Render one object. (ox, oy) is the origin of the positioning context."""
        t = obj.get("type")
        method = getattr(self, f"_render_{t}", None)
        if method is None:
            return self._render_unknown(obj, ox, oy)
        return method(obj, ox, oy)

    def _render_rect(self, obj, ox, oy):
        x, y, w, h = _box(obj)
        css = {}
        fill = self.tokens.color(obj.get("fill"))
        if fill is not None and not isinstance(obj.get("fill"), dict):
            css["background"] = fill
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
            text = "".join(
                s.get("text", "") if isinstance(s, dict) else str(s)
                for s in obj["spans"]
            )
        body = html.escape(text or "")
        attrs = self._common(obj, ox + x, oy + y, w, h,
                             extra_classes=classes, extra_css=css)
        return f"<div {attrs}><span>{body}</span></div>"

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
        fill = self.tokens.color(obj.get("fill"))
        if fill is not None and not isinstance(obj.get("fill"), dict):
            css["background"] = fill
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
        paint = self._paint_css(obj, fillable=True)
        attrs = self._common(obj, ox + minx - pad, oy + miny - pad, bw, bh)
        svg = (
            f'<svg aria-hidden="true" width="{bw:.2f}" height="{bh:.2f}" '
            f'viewBox="0 0 {bw:.2f} {bh:.2f}" '
            f'style="position:absolute;inset:0;overflow:visible">'
            f'<{tag} points="{local}" style="{html.escape(paint)}"/></svg>'
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
        paint = self._paint_css(obj, fillable=obj.get("fill") is not None)
        attrs = self._common(obj, ox + minx - pad, oy + miny - pad, bw, bh)
        svg = (
            f'<svg aria-hidden="true" width="{bw:.2f}" height="{bh:.2f}" '
            f'viewBox="0 0 {bw:.2f} {bh:.2f}" '
            f'style="position:absolute;inset:0;overflow:visible">'
            f'<path d="{d}" style="{html.escape(paint)}"/></svg>'
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
        paint = self._paint_css(obj, fillable=obj.get("fill") is not None)
        attrs = self._common(obj, ox, oy, 0, 0, extra_css={"overflow": "visible"})
        svg = (
            f'<svg aria-hidden="true" width="1" height="1" overflow="visible" '
            f'style="position:absolute;overflow:visible">'
            f'<path d="{html.escape(d)}" style="{html.escape(paint)}"/></svg>'
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


# Canonical preset -> (w, h) table, mirrored from tooling/validate.py::_canvas_wh
# (keys match models.framegraph.PagePreset). Keep in sync with that table.
# Mirrors CanvasResolver.PRESETS / models.PagePreset (kept in sync — see
# tests/test_framegraph_to_html.py::test_preset_table_matches_model_page_presets).
_CANVAS_PRESETS: dict[str, tuple[float, float]] = {
    "A3": (842, 1191), "A4": (595, 842), "A5": (419.5, 595.3), "Letter": (612, 792),
    "Legal": (612, 1008), "Tabloid": (792, 1224), "deck-16x9": (1920, 1080), "deck-4x3": (1024, 768),
    "square": (1080, 1080), "phone": (390, 844), "tablet": (834, 1112), "web": (1280, 800),
    "instagram-square": (1080, 1080), "instagram-portrait": (1080, 1350), "instagram-landscape": (1080, 566), "instagram-story": (1080, 1920),
    "facebook-post": (1200, 630), "facebook-cover": (820, 312), "facebook-story": (1080, 1920), "twitter-post": (1600, 900),
    "twitter-header": (1500, 500), "linkedin-post": (1200, 627), "linkedin-cover": (1584, 396), "youtube-thumbnail": (1280, 720),
    "youtube-banner": (2560, 1440), "tiktok-video": (1080, 1920), "pinterest-pin": (1000, 1500), "snapchat": (1080, 1920),
    "story": (1080, 1920), "1x1": (1080, 1080), "4x5": (1080, 1350), "5x4": (1350, 1080),
    "9x16": (1080, 1920), "16x9": (1920, 1080), "2x3": (1080, 1620), "3x2": (1620, 1080),
    "1.91x1": (1200, 628), "3x1": (1500, 500),
    # Book trim sizes (points @ 72dpi — mirror CanvasResolver.PRESETS).
    "book-pocket": (288, 432), "book-mass-market": (306, 494.6), "book-trade": (360, 576),
    "book-novel": (378, 576), "book-digest": (396, 612), "book-6x9": (432, 648),
    "book-7x10": (504, 720), "book-8x10": (576, 720), "book-textbook": (612, 792),
    "book-square-8": (576, 576), "book-picture": (612, 612), "book-square-10": (720, 720),
    "book-coffee-table": (648, 864), "book-art-10x12": (720, 864), "book-art-11x14": (792, 1008),
}


def canvas_size(page: dict, default=(800, 600)) -> tuple[float, float]:
    """Resolve a page's canvas to (w, h): inline size, named preset, or default."""
    canvas = page.get("canvas")
    if isinstance(canvas, str):                       # bare preset, e.g. "deck-16x9"
        return _CANVAS_PRESETS.get(canvas, default)
    if isinstance(canvas, dict):
        if canvas.get("size"):
            return _num(canvas["size"][0]), _num(canvas["size"][1])
        if canvas.get("preset"):                      # {preset: "A4"}
            return _CANVAS_PRESETS.get(canvas["preset"], default)
    return default


def render_page(page: dict, tokens: Tokens, index: int) -> str:
    renderer = Renderer(tokens)
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
        f'<div class="framegraph-page" id="page-{_css_ident(page.get("id", index))}" '
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
        f'<div class="framegraph-page fg-flow-note" '
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
        # <figure>/<figcaption> associate the caption with the artifact, and
        # aria-labelledby gives the figure its accessible name.
        blocks.append(
            f'<figure class="fg-figure" role="group" aria-labelledby="{cap_id}">\n'
            f"{figcaption}\n{page_html}\n</figure>"
        )

    doc_title = html.escape(str(doc.get("title") or "FrameGraph render"))
    description = html.escape(str(doc.get("description") or ""))
    lang = html.escape(str(doc.get("lang") or "en"))

    return f"""<!DOCTYPE html>
<html lang="{lang}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="generator" content="framegraph_to_html.py">
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
# CLI                                                                          #
# --------------------------------------------------------------------------- #


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Rebuild an HTML page from a FrameGraph v2 (diagram) document."
    )
    parser.add_argument("input", help="FrameGraph .yaml / .yml / .json document")
    parser.add_argument("-o", "--output", help="output .html (default: alongside input)")
    parser.add_argument("--schema", help="path to framegraph schema JSON (for --validate)")
    parser.add_argument("--validate", action="store_true",
                        help="validate against --schema before rendering")
    args = parser.parse_args(argv)

    doc = load_document(args.input)
    if args.validate:
        maybe_validate(doc, args.schema)

    html_text = render_document(doc)

    out = args.output or os.path.splitext(args.input)[0] + ".html"
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(html_text)

    n_pages = len(doc.get("pages") or [])
    print(f"Wrote {out}  ({n_pages} page(s))")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
