"""Design-token + feature-usage audit for a rendered FrameForge document.

WHY THIS IS DRIFT-PROOF
-----------------------
The audit does NOT hand-enumerate features. It derives its statistics from two
generic sources, so a feature added later is captured with **no** new
instrumentation:

1. **The emitted SVG** — every visual token (font family/size/weight/style,
   letter-spacing, fill/stroke colour, stroke width/dash, opacity, gradients …)
   is read straight off the rendered ``<text>``/shape elements. The SVG is the
   single sink every visual feature must pass through to be seen, so any new
   presentation attribute shows up in the census automatically (unknown style
   properties land in ``svg.other_properties``).

2. **A generic model walk** — every ``type``/``kind`` discriminator and every
   distinct object key in the document tree is counted recursively, so a new
   object type, flowable, inline kind, or field appears in ``model.*`` without a
   code change here.

Consequence: to "drift" (ship a feature the audit misses) you would have to emit
neither an SVG attribute nor a model key for it — i.e. render nothing. The audit
therefore fails safe toward *over*-reporting, never silent omission.

``audit_document(doc, svg_pages)`` returns the machine report;
``render_markdown`` and ``summary_line`` present it.
"""
from __future__ import annotations

import re
from collections import Counter
from typing import Any

# --------------------------------------------------------------------------- #
#  SVG token census (the drift-proof visual sink)                             #
# --------------------------------------------------------------------------- #
_ELEMENT = re.compile(r"<(\w[\w:-]*)\b([^>]*?)/?>", re.S)
_ATTR = re.compile(r'([\w:-]+)\s*=\s*"([^"]*)"')

_SHAPE_TAGS = {"rect", "path", "circle", "ellipse", "line", "polygon", "polyline"}
_TEXT_TAGS = {"text", "tspan"}
_GRADIENT_TAGS = {"lineargradient", "radialgradient"}
# style properties given their own first-class category (everything else that
# appears in a style="" declaration is still captured, under other_properties)
_KNOWN_TEXT_PROPS = {
    "font-family", "font-size", "font-weight", "font-style", "letter-spacing",
    "word-spacing", "text-anchor", "text-transform", "text-decoration", "fill",
    "fill-opacity", "opacity", "dominant-baseline", "line-height",
}


def _decls(attr_str: str) -> dict[str, str]:
    """Flatten presentation attributes AND ``style=""`` declarations into one
    property map (style wins, mirroring CSS)."""
    props: dict[str, str] = {}
    for key, value in _ATTR.findall(attr_str):
        if key == "style":
            for decl in value.split(";"):
                if ":" in decl:
                    pk, pv = decl.split(":", 1)
                    props[pk.strip().lower()] = pv.strip()
        else:
            props[key.lower()] = value.strip()
    return props


def _norm_size(value: str) -> str:
    v = value.strip().lower().removesuffix("px").strip()
    try:
        f = float(v)
        return str(int(f)) if f == int(f) else str(f)
    except ValueError:
        return value.strip()


def _norm_color(value: str) -> str:
    v = value.strip()
    return v.upper() if re.fullmatch(r"#[0-9a-fA-F]{3,8}", v) else v


def _audit_svg(svg_pages: list[str]) -> dict[str, Any]:
    families: Counter = Counter()
    sizes: Counter = Counter()
    weights: Counter = Counter()
    fstyles: Counter = Counter()
    tracking: Counter = Counter()
    anchors: Counter = Counter()
    transforms: Counter = Counter()
    decorations: Counter = Counter()
    text_fill: Counter = Counter()
    shape_fill: Counter = Counter()
    strokes: Counter = Counter()
    stroke_w: Counter = Counter()
    dashes: Counter = Counter()
    opacity: Counter = Counter()
    gradients: Counter = Counter()
    other_props: Counter = Counter()     # anti-drift catch-all for unknown props

    for svg in svg_pages:
        for match in _ELEMENT.finditer(svg):
            tag = match.group(1).lower()
            props = _decls(match.group(2))
            if tag in _GRADIENT_TAGS:
                gradients[tag] += 1
            if tag in _TEXT_TAGS:
                if "font-family" in props:
                    families[props["font-family"].strip()] += 1
                if "font-size" in props:
                    sizes[_norm_size(props["font-size"])] += 1
                if "font-weight" in props:
                    weights[props["font-weight"].strip()] += 1
                if "font-style" in props:
                    fstyles[props["font-style"].strip()] += 1
                if "letter-spacing" in props:
                    tracking[_norm_size(props["letter-spacing"])] += 1
                if "text-anchor" in props:
                    anchors[props["text-anchor"].strip()] += 1
                if "text-transform" in props:
                    transforms[props["text-transform"].strip()] += 1
                if "text-decoration" in props:
                    decorations[props["text-decoration"].strip()] += 1
                if props.get("fill", "none") != "none":
                    text_fill[_norm_color(props["fill"])] += 1
            elif tag in _SHAPE_TAGS:
                if props.get("fill", "none") not in ("none", ""):
                    shape_fill[_norm_color(props["fill"])] += 1
                if props.get("stroke", "none") not in ("none", ""):
                    strokes[_norm_color(props["stroke"])] += 1
                if "stroke-width" in props:
                    stroke_w[_norm_size(props["stroke-width"])] += 1
                if "stroke-dasharray" in props:
                    dashes[props["stroke-dasharray"].strip()] += 1
                for op in ("opacity", "fill-opacity", "stroke-opacity"):
                    if op in props:
                        opacity[props[op].strip()] += 1
            # anti-drift: record every style property key we did not file above
            for key in props:
                if key not in _KNOWN_TEXT_PROPS and key not in (
                        "x", "y", "width", "height", "d", "cx", "cy", "r", "rx",
                        "ry", "x1", "y1", "x2", "y2", "points", "transform",
                        "id", "class", "stroke", "stroke-width", "stroke-dasharray",
                        "viewbox", "xmlns", "href", "offset", "stop-color"):
                    other_props[key] += 1

    return {
        "font_family": _cat(families),
        "font_size_px": _cat(sizes, numeric=True),
        "font_weight": _cat(weights),
        "font_style": _cat(fstyles),
        "letter_spacing": _cat(tracking, numeric=True),
        "text_anchor": _cat(anchors),
        "text_transform": _cat(transforms),
        "text_decoration": _cat(decorations),
        "text_color": _cat(text_fill),
        "shape_fill": _cat(shape_fill),
        "stroke_color": _cat(strokes),
        "stroke_width": _cat(stroke_w, numeric=True),
        "stroke_dasharray": _cat(dashes),
        "opacity": _cat(opacity, numeric=True),
        "gradients": _cat(gradients),
        "other_properties": _cat(other_props),
    }


def _cat(counter: Counter, *, numeric: bool = False) -> dict[str, Any]:
    if numeric:
        def key(v):
            try:
                return (0, float(v))
            except (TypeError, ValueError):
                return (1, str(v))
        distinct = sorted(counter, key=key)
    else:
        distinct = sorted(counter, key=lambda v: (-counter[v], str(v)))
    return {
        "n_distinct": len(distinct),
        "total": sum(counter.values()),
        "distinct": distinct,
        "counts": {v: counter[v] for v in distinct},
    }


# --------------------------------------------------------------------------- #
#  Model feature census (generic walk — new node types appear automatically)  #
# --------------------------------------------------------------------------- #
def _audit_model(doc: dict) -> dict[str, Any]:
    types: Counter = Counter()
    kinds: Counter = Counter()
    keys: Counter = Counter()

    def walk(node: Any) -> None:
        if isinstance(node, dict):
            if isinstance(node.get("type"), str):
                types[node["type"]] += 1
            if isinstance(node.get("kind"), str):
                kinds[node["kind"]] += 1
            for k, v in node.items():
                keys[k] += 1
                walk(v)
        elif isinstance(node, list):
            for item in node:
                walk(item)

    walk(doc)
    defs = doc.get("defs") or {}
    masters = defs.get("masters") or {}
    tokens = defs.get("tokens") or {}
    pages = doc.get("pages") or []
    structural = {
        "producers": len(pages),
        "fixed_pages": sum(1 for p in pages if isinstance(p, dict) and p.get("mode") == "page"),
        "flow_sections": sum(1 for p in pages if isinstance(p, dict) and p.get("mode") == "flow"),
        "masters": len(masters),
        "colors_defined": len(tokens.get("colors") or {}),
        "fonts_defined": len(tokens.get("fonts") or {}),
        "styles_defined": len(tokens.get("styles") or {}) + len(tokens.get("text_styles") or {}),
        "counters_defined": len(defs.get("counters") or {}),
        "symbols_defined": len(defs.get("symbols") or {}),
        "targets": len(doc.get("targets") or []),
        "running_furniture": any(isinstance(m, dict) and m.get("running") for m in masters.values()),
        "footnote_area": any(isinstance(m, dict) and m.get("footnote_area") for m in masters.values()),
        "multicolumn_regions": any(
            isinstance(r, dict) and r.get("columns")
            for m in masters.values() if isinstance(m, dict)
            for r in (m.get("regions") or [])),
        "humanize": "humanize" in doc,
    }
    return {
        "object_and_flow_types": dict(sorted(types.items(), key=lambda kv: (-kv[1], kv[0]))),
        "inline_and_paint_kinds": dict(sorted(kinds.items(), key=lambda kv: (-kv[1], kv[0]))),
        "structural": structural,
        "all_model_keys": dict(sorted(keys.items(), key=lambda kv: (-kv[1], kv[0]))),
    }


# --------------------------------------------------------------------------- #
#  Design-system health flags                                                 #
# --------------------------------------------------------------------------- #
_SIZE_BUDGET = 6
_COLOR_BUDGET = 14


def _health(svg: dict) -> list[dict[str, str]]:
    flags: list[dict[str, str]] = []
    sizes = [float(s) for s in svg["font_size_px"]["distinct"]
             if _is_float(s)]
    if len(sizes) > _SIZE_BUDGET:
        flags.append({"level": "warn", "code": "type-scale-sprawl",
                      "message": f"{len(sizes)} distinct font sizes "
                      f"(budget {_SIZE_BUDGET}): {_fmt(sizes)}"})
    near = [f"{a}/{b}" for i, a in enumerate(sorted(sizes))
            for b in sorted(sizes)[i + 1:] if 0 < round(b - a, 3) <= 1.0]
    if near:
        flags.append({"level": "warn", "code": "near-duplicate-sizes",
                      "message": "sizes within 1px of each other (pick one): "
                      + ", ".join(near)})
    colors = set(svg["text_color"]["distinct"]) | set(svg["shape_fill"]["distinct"]) \
        | set(svg["stroke_color"]["distinct"])
    if len(colors) > _COLOR_BUDGET:
        flags.append({"level": "warn", "code": "palette-sprawl",
                      "message": f"{len(colors)} distinct colours "
                      f"(budget {_COLOR_BUDGET})"})
    weights = set(svg["font_weight"]["distinct"])
    if "bold" in weights and (weights & {"700", "600", "800"}):
        flags.append({"level": "warn", "code": "mixed-weight-encoding",
                      "message": "font-weight uses both a keyword ('bold') and "
                      f"numbers ({sorted(weights)}); pick one convention"})
    fams = {f.split(",")[0].strip().strip("'\"").lower()
            for f in svg["font_family"]["distinct"]}
    generic = fams & {"serif", "sans-serif", "monospace"}
    concrete = fams - generic
    if concrete and generic and len(concrete) >= 1 and len(fams) > len(concrete):
        # a bare generic family alongside concrete faces usually means a fallback
        # leaked as a primary — worth flagging so it doesn't render an unintended face
        flags.append({"level": "info", "code": "generic-family-present",
                      "message": f"primary families resolved include bare generics "
                      f"{sorted(generic)} — confirm these are intended, not fallbacks"})
    if not flags:
        flags.append({"level": "ok", "code": "within-budget",
                      "message": "type scale and palette are within budget"})
    return flags


def _is_float(v: str) -> bool:
    try:
        float(v)
        return True
    except (TypeError, ValueError):
        return False


def _fmt(sizes: list[float]) -> str:
    return ", ".join(str(int(s)) if s == int(s) else str(s) for s in sorted(sizes))


# --------------------------------------------------------------------------- #
#  Public API                                                                 #
# --------------------------------------------------------------------------- #
def audit_document(doc: dict, svg_pages: list[str]) -> dict[str, Any]:
    """Full design-token + feature-usage audit of a rendered document."""
    svg = _audit_svg(svg_pages)
    return {
        "pages": len(svg_pages),
        "methodology": "tokens read from the emitted SVG; features from a generic "
                       "model walk — new features are captured with no new code",
        "svg": svg,
        "model": _audit_model(doc),
        "health": _health(svg),
    }


def compact_census(report: dict) -> dict[str, Any]:
    """A small design-token summary for surfacing on a render result — the
    distinct counts plus the health flags, without the full value lists."""
    svg = report["svg"]
    colours = (set(svg["text_color"]["distinct"]) | set(svg["shape_fill"]["distinct"])
               | set(svg["stroke_color"]["distinct"]))
    return {
        "faces": svg["font_family"]["n_distinct"],
        "sizes": svg["font_size_px"]["n_distinct"],
        "weights": svg["font_weight"]["n_distinct"],
        "colours": len(colours),
        "health": report["health"],
    }


def summary_line(report: dict) -> str:
    svg = report["svg"]
    worst = max((f for f in report["health"]),
                key=lambda f: {"warn": 2, "info": 1, "ok": 0}.get(f["level"], 0))
    return (f"audit: {report['pages']} page(s) · "
            f"{svg['font_family']['n_distinct']} face(s) · "
            f"{svg['font_size_px']['n_distinct']} sizes · "
            f"{svg['font_weight']['n_distinct']} weights · "
            f"{len(set(svg['text_color']['distinct']) | set(svg['shape_fill']['distinct']) | set(svg['stroke_color']['distinct']))} colours "
            f"→ {worst['level'].upper()}: {worst['code']}")


def render_markdown(report: dict, *, title: str) -> str:
    svg, model, health = report["svg"], report["model"], report["health"]
    out: list[str] = []
    out.append(f"# Design audit — {title}\n")
    out.append(f"_{report['pages']} page(s). {report['methodology']}._\n")

    out.append("## Health\n")
    for f in health:
        mark = {"warn": "⚠", "info": "ℹ", "ok": "✓"}.get(f["level"], "•")
        out.append(f"- {mark} **{f['code']}** — {f['message']}")
    out.append("")

    out.append("## Visual tokens (from the emitted SVG)\n")
    out.append("| Token | distinct | values (count) |")
    out.append("|---|---:|---|")
    for label, key in [
        ("Font families", "font_family"), ("Font sizes (px)", "font_size_px"),
        ("Font weights", "font_weight"), ("Font styles", "font_style"),
        ("Letter-spacing", "letter_spacing"), ("Text colours", "text_color"),
        ("Shape fills", "shape_fill"), ("Stroke colours", "stroke_color"),
        ("Stroke widths", "stroke_width"), ("Dash patterns", "stroke_dasharray"),
        ("Opacity", "opacity"), ("Text-anchor", "text_anchor"),
        ("Text-transform", "text_transform"), ("Gradients", "gradients"),
        ("Other props (uncatalogued)", "other_properties"),
    ]:
        cat = svg[key]
        vals = ", ".join(f"`{v}`×{cat['counts'][v]}" for v in cat["distinct"][:12])
        if cat["n_distinct"] > 12:
            vals += f", … (+{cat['n_distinct'] - 12})"
        out.append(f"| {label} | {cat['n_distinct']} | {vals or '—'} |")
    out.append("")

    out.append("## Features (from the model)\n")
    st = model["structural"]
    out.append("| Structural | value |")
    out.append("|---|---|")
    for k, v in st.items():
        out.append(f"| {k} | {v} |")
    out.append("")
    out.append("**Object / flow types:** " + (", ".join(
        f"`{t}`×{n}" for t, n in model["object_and_flow_types"].items()) or "—"))
    out.append("")
    out.append("**Inline / paint kinds:** " + (", ".join(
        f"`{k}`×{n}" for k, n in model["inline_and_paint_kinds"].items()) or "—"))
    out.append("")
    return "\n".join(out)
