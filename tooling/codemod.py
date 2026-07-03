#!/usr/bin/env python3
"""
codemod.py — migrate a FrameGraph v2 document to HEAD conventions.

Applies the mechanical migrations the patch series requires:

  1. P3 stroke single-form (BREAKING) — an inline-geometry `stroke`
     {color,width,dash,linecap,linejoin,arrow_*,opacity} is split:
        color  -> `stroke`        (paint only)
        rest   -> `stroke_style`  (inline geometry bundle; merged if absent)
  2. P4 `size` -> `sizing` — a content-sizing object literal under the colliding
     `size` key is renamed (numeric `size` on an `icon` is left alone).
  3. Gradient stops: `offset` -> `position` (2.2.0; %-normalised).
  4. (optional, --normalize-aliases) renderer-shortcut primitives ->
     grammar-normative forms:  circle -> ellipse,  polygon -> closed polyline,
     curve/bezier -> single-segment path.
  5. (optional, --bump) set document `version` to the HEAD version.

Round-trips via PyYAML (comments/key-order are not preserved — fine for the
generated fixtures). Use --in-place to overwrite, else writes <name>.head.<ext>.

Usage:
    python3 codemod.py doc.fg.yaml [...] [--in-place] [--normalize-aliases] [--bump]
"""
from __future__ import annotations

import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.normpath(os.path.join(HERE, "..", "docs", "models")))
import yaml  # noqa: E402

try:
    import framegraph as fg  # noqa: E402
    HEAD_VERSION = fg.HEAD_VERSION
except Exception:  # noqa: BLE001
    HEAD_VERSION = "2.2.0"

GEOMETRY_KEYS = ("width", "dash", "linecap", "linejoin", "arrow_start", "arrow_end", "opacity")
# 2.2.0: stroke geometry migrates to CSS-named Style properties (the style module).
GEOM_TO_CSS = {
    "width": "stroke_width", "dash": "stroke_dasharray", "linecap": "stroke_linecap",
    "linejoin": "stroke_linejoin", "opacity": "stroke_opacity",
    "arrow_start": "arrow_start", "arrow_end": "arrow_end",
}


class Stats:
    def __init__(self):
        self.stroke = self.size = self.grad = self.alias = self.v01 = 0


def _pct(v):
    if isinstance(v, str) and v.strip().endswith("%"):
        return float(v.strip()[:-1]) / 100.0
    return v


def migrate(node, stats: Stats, normalize_aliases: bool):
    if isinstance(node, list):
        return [migrate(x, stats, normalize_aliases) for x in node]
    if not isinstance(node, dict):
        return node

    # gradient stop offset -> position (2.2.0: position is authoritative)
    if "offset" in node and "color" in node and "position" not in node:
        o = node.pop("offset")
        node["position"] = (f"{o*100:g}%" if isinstance(o, (int, float)) and o <= 1 else o)
        stats.grad += 1

    t = node.get("type")

    # 1. stroke single-form -> paint in `stroke`, CSS-named geometry in `stroke_style` Style
    if isinstance(node.get("stroke"), dict) and any(k in node["stroke"] for k in GEOMETRY_KEYS):
        s = node.pop("stroke")
        geom = {GEOM_TO_CSS[k]: s[k] for k in GEOMETRY_KEYS if k in s}
        if "color" in s:
            node["stroke"] = s["color"]
        if geom:
            existing = node.get("stroke_style")
            if isinstance(existing, dict):
                existing.update({k: v for k, v in geom.items() if k not in existing})
            elif isinstance(existing, str):
                node.setdefault("meta", {})["_codemod_stroke_geometry"] = geom
            else:
                node["stroke_style"] = geom
        stats.stroke += 1

    # 2. size -> sizing (content sizing object only; not numeric icon size)
    if "size" in node and isinstance(node["size"], dict) and t != "icon":
        node["sizing"] = node.pop("size")
        stats.size += 1
    elif "size" in node and isinstance(node["size"], dict) and t == "icon":
        # an icon with a dict `size` is actually content sizing mislabeled
        node["sizing"] = node.pop("size")
        stats.size += 1

    # 4. alias normalisation (optional; changes representation, not appearance)
    if normalize_aliases and t in ("circle", "polygon", "curve", "bezier"):
        node = _normalize_alias(node, stats)
        t = node.get("type")

    # recurse
    for k, v in list(node.items()):
        node[k] = migrate(v, stats, normalize_aliases)
    return node


def _normalize_alias(node, stats: Stats):
    t = node["type"]
    if t == "circle":
        r = node.pop("r")
        node["type"] = "ellipse"
        node["rx"] = node["ry"] = r
        stats.alias += 1
    elif t == "polygon":
        node["type"] = "polyline"
        node["closed"] = True
        stats.alias += 1
    elif t in ("curve", "bezier"):
        f = node.pop("from"); to = node.pop("to")
        c1 = node.pop("control1", None) or node.pop("c1", None) or f
        c2 = node.pop("control2", None) or node.pop("c2", None) or c1
        node["type"] = "path"
        node["d"] = [["M", f[0], f[1]], ["C", c1[0], c1[1], c2[0], c2[1], to[0], to[1]]]
        node.pop("control1", None); node.pop("control2", None)
        node.pop("c1", None); node.pop("c2", None)
        stats.alias += 1
    return node


def migrate_stroke_bundles(doc, stats):
    """2.2.0: tokens.stroke_styles entries are Style projections. Rewrite a legacy
    geometry bundle {color,width,dash,…} to CSS-named Style props."""
    m = {"color": "stroke", "width": "stroke_width", "dash": "stroke_dasharray",
         "linecap": "stroke_linecap", "linejoin": "stroke_linejoin", "opacity": "stroke_opacity"}
    ss = (((doc.get("defs") or {}).get("tokens") or {}).get("stroke_styles") or {})
    for name, b in list(ss.items()):
        if isinstance(b, dict) and any(k in b for k in ("width", "dash", "linecap", "linejoin")):
            ss[name] = {m.get(k, k): v for k, v in b.items()}
            stats.stroke += 1


# ── v0.1 dialect lift (issue #33 — the deck-corpus conversion path) ──────

_V01_TS = {"size": "font_size", "weight": "font_weight",
           "v_align": "vertical_align"}


def _translate_text_style(style, fonts, default_nowrap=True):
    """One v0.1 text-style dict → v2 names. The old keys VALIDATE in v2 as
    unrelated CSS props (font = shorthand, size = box width…) — rename,
    don't just carry. v0.1 wrapped ONLY under `wrap: true`; v2 wraps by
    default, so a style without `wrap` pins `white_space: nowrap` (spans
    pass default_nowrap=False — runs never wrap themselves)."""
    out = {}
    wrapped = False
    for k, v in style.items():
        if k == "font":
            fam = (fonts or {}).get(v, v)
            if isinstance(fam, dict):                  # already a font def
                fam = fam.get("family", v)
            out["font_family"] = [p.strip().strip("'\"")
                                  for p in str(fam).split(",")]
        elif k == "wrap":
            wrapped = bool(v)                 # v2 wraps by default
        else:
            out[_V01_TS.get(k, k)] = v
    if default_nowrap and not wrapped:
        out["white_space"] = "nowrap"
    return out


def _lift_v01_text_styles(tokens):
    fonts = tokens.get("fonts") or {}
    for name, style in list((tokens.get("text_styles") or {}).items()):
        if isinstance(style, dict):
            tokens["text_styles"][name] = _translate_text_style(style, fonts)
    for name, fam in list(fonts.items()):
        if isinstance(fam, str):              # CSS string -> v2 font def
            fonts[name] = {"family": fam}


def _lift_inline_text_styles(node, fonts):
    """Inline ``style: {…}`` dicts on v0.1 objects carry the same legacy
    keys as the token styles — translate them everywhere."""
    if isinstance(node, list):
        for item in node:
            _lift_inline_text_styles(item, fonts)
        return
    if not isinstance(node, dict):
        return
    style = node.get("style")
    if isinstance(style, dict):
        node["style"] = _translate_text_style(style, fonts)
    if "type" in node and isinstance(node.get("stroke_width"), (int, float)):
        # v0.1 flat stroke geometry on the object -> stroke_style (P3)
        ss = node.get("stroke_style")
        if isinstance(ss, dict):
            ss.setdefault("stroke_width", node.pop("stroke_width"))
        elif ss is None:
            node["stroke_style"] = {"stroke_width": node.pop("stroke_width")}
    for span in (node.get("spans") or []):
        # v0.1 spans carry style keys flat; v2 Span allows text/style/lang
        if not isinstance(span, dict):
            continue
        extras = {k: span.pop(k) for k in list(span)
                  if k not in ("text", "style", "lang")}
        if extras:
            merged = _translate_text_style(extras, fonts,
                                           default_nowrap=False)
            if isinstance(span.get("style"), dict):
                merged.update(span["style"])
            span["style"] = merged
    for key, value in node.items():
        if key != "spans":                    # handled above, run-scoped
            _lift_inline_text_styles(value, fonts)


def _lower_chip_rows(node, component_defs):
    """v0.1 `chip_row` (a compositional renderer type) has no v2
    counterpart — lower each into a core group of pill rects + texts,
    reproducing render_chip_row's layout: left-to-right from `origin`
    with `gap`, explicit item width or the auto-size max(20, len*6+12),
    chip def supplying fill / text_style / corner radius. Returns the
    number of rows lowered."""
    lowered = 0
    if isinstance(node, list):
        for item in node:
            lowered += _lower_chip_rows(item, component_defs)
        return lowered
    if not isinstance(node, dict):
        return lowered
    for key, value in list(node.items()):
        if key == "objects" and isinstance(value, list):
            for i, obj in enumerate(value):
                if isinstance(obj, dict) and obj.get("type") == "chip_row":
                    value[i] = _chip_row_group(obj, component_defs)
                    lowered += 1
        lowered += _lower_chip_rows(value, component_defs)
    return lowered


def _chip_row_group(obj, component_defs):
    chip = (component_defs or {}).get("chip") or {}
    x, y = (float(v) for v in obj.get("origin") or [0, 0])
    gap = float(obj.get("gap") or 0)
    height = float(obj.get("height") or 16)
    radius = ((chip.get("geometry") or {}).get("radius") or 0)
    fill = obj.get("fill", chip.get("fill", "none"))
    style = obj.get("style", chip.get("text_style", "tiny"))
    children, cursor = [], x
    for item in obj.get("items") or []:
        if isinstance(item, dict):
            label = str(item.get("text", ""))
            width = float(item.get("width") or max(20, len(label) * 6 + 12))
        else:
            label = str(item)
            width = float(max(20, len(label) * 6 + 12))
        box = [cursor, y, width, height]
        # the pill is decoration behind its label (exempts it from the
        # free-group overlap lint, matching the decks' background-rect idiom)
        rect = {"type": "rect", "box": box, "fill": fill, "decorative": True}
        if radius:
            rect["radius"] = radius
        if obj.get("stroke") is not None:
            rect["stroke"] = obj["stroke"]
        children.append(rect)
        children.append({"type": "text", "box": list(box), "text": label,
                         "style": style})
        cursor += width + gap
    group = {"type": "group", "children": children}
    if obj.get("id"):
        group["id"] = obj["id"]
    return group


def _v01_profile(kind):
    if not kind:
        return None
    if "diagram" in kind:
        return "diagram"
    if "deck" in kind or "presentation" in kind:
        return "deck"
    return None


def lift_v01(doc, stats: Stats):
    """Lift a v0.1 envelope (scene-form or deck/slides-form) to the v2
    envelope, then run the standard HEAD migrations. v2 documents pass
    through unchanged."""
    if not isinstance(doc, dict) or not ("scene" in doc or "deck" in doc
                                         or "slides" in doc):
        return doc
    stats.v01 += 1

    kind = doc.pop("kind", None)
    out = {"dsl": doc.get("dsl", "FrameGraph"), "version": HEAD_VERSION}
    profile = _v01_profile(kind)
    if profile:
        out["profile"] = profile

    if "scene" in doc:                                   # scene-form
        scene = doc.pop("scene") or {}
        if scene.get("name"):
            out["title"] = scene["name"]
        if scene.get("description"):
            out["description"] = scene["description"]
        visual = doc.pop("visual", None) or {}
        tokens = visual.get("tokens") or {}
        if tokens:
            _lift_v01_text_styles(tokens)
            out["defs"] = {"tokens": tokens}
        page = {"mode": "page", "id": scene.get("id") or "page-1"}
        if scene.get("canvas"):
            page["canvas"] = scene["canvas"]
        if scene.get("rendering_contract"):
            page["rendering"] = scene["rendering_contract"]
        semantic = doc.pop("semantic", None)
        if semantic:
            page["semantic"] = semantic
        page["layers"] = visual.get("layers") or []
        _lift_inline_text_styles(page["layers"], tokens.get("fonts"))
        out["pages"] = [page]
    else:                                                # deck/slides-form
        deck = doc.pop("deck", None) or {}
        canvas = deck.get("canvas")
        defs = {}
        tokens = deck.get("tokens") or {}
        if tokens:
            _lift_v01_text_styles(tokens)
            defs["tokens"] = tokens
        pages = []
        slides = doc.pop("slides", None) or []
        for i, slide in enumerate(slides, start=1):
            page = {"mode": "page",
                    "id": slide.get("id") or f"slide-{i}"}
            if canvas:
                page["canvas"] = canvas
            meta = {k: slide[k] for k in ("slide", "title")
                    if slide.get(k) is not None}
            if meta:
                page["meta"] = meta
            if slide.get("notes"):
                page["notes"] = slide["notes"]
            # v0.1 deck text painted past its authoring box and was never
            # truncated; v2 defaults to wrap-then-clip — pin the legacy
            # semantics so migration cannot silently lose content
            page["rendering"] = {"text": {"overflow": "visible"}}
            page["layers"] = (slide.get("visual") or {}).get("layers") or []
            pages.append(page)
        _lift_inline_text_styles(pages, tokens.get("fonts"))
        component_defs = dict(deck.get("component_defs") or {})
        lowered = _lower_chip_rows(pages, component_defs)
        if lowered and "chip" in component_defs and not any(
                obj.get("type") == "component"
                for page in pages for layer in page.get("layers") or []
                for obj in layer.get("objects") or []
                if isinstance(obj, dict)):
            # the chip def is baked into the lowered rows — dropping it is
            # lossless; unconsumed defs are kept (dropping those is not)
            component_defs.pop("chip")
        if component_defs:
            defs["components"] = component_defs
        if defs:
            out["defs"] = defs
        out["pages"] = pages

    if kind:
        out.setdefault("meta", {})["kind"] = kind
    out.setdefault("meta", {})["migrated_from"] = \
        f"FrameGraph v0.1 (document version {doc.get('version')})"
    for key in ("dsl", "version", "scene", "semantic", "visual", "deck",
                "slides"):
        doc.pop(key, None)
    v2_keys = {"profile", "title", "description", "lang", "defs", "targets",
               "pages", "meta", "text_contract"}
    for k, v in doc.items():           # remaining top-level keys carry over;
        if k in v2_keys:               # unknown ones ride in meta (v2 Document
            out.setdefault(k, v)       # forbids extras)
        else:
            out.setdefault("meta", {})[k] = v

    migrate_stroke_bundles(out, stats)
    return migrate(out, stats, normalize_aliases=False)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("documents", nargs="+")
    ap.add_argument("--in-place", action="store_true")
    ap.add_argument("--normalize-aliases", action="store_true",
                    help="also rewrite circle/polygon/curve to ellipse/polyline/path")
    ap.add_argument("--bump", action="store_true", help=f"set version to {HEAD_VERSION}")
    ap.add_argument("--from-v01", action="store_true",
                    help="lift a v0.1 envelope (scene: or deck:/slides:) to v2 first")
    args = ap.parse_args(argv)

    total = Stats()
    for path in args.documents:
        doc = yaml.safe_load(open(path, encoding="utf-8"))
        st = Stats()
        if args.from_v01:
            doc = lift_v01(doc, st)
        migrate_stroke_bundles(doc, st)
        doc = migrate(doc, st, args.normalize_aliases)
        if args.bump and isinstance(doc, dict) and doc.get("dsl") == "FrameGraph":
            doc["version"] = HEAD_VERSION
        if args.in_place:
            out = path
        else:
            base, ext = os.path.splitext(path)
            out = f"{base}.head{ext}"
        with open(out, "w", encoding="utf-8") as fh:
            if out.lower().endswith(".json"):
                json.dump(doc, fh, indent=2, ensure_ascii=False)
                fh.write("\n")
            else:
                yaml.safe_dump(doc, fh, sort_keys=False, allow_unicode=True, width=120)
        print(f"{os.path.basename(path)} -> {os.path.basename(out)} "
              f"(v01:{st.v01} stroke:{st.stroke} size→sizing:{st.size} grad:{st.grad} alias:{st.alias})")
        for f in ("stroke", "size", "grad", "alias", "v01"):
            setattr(total, f, getattr(total, f) + getattr(st, f))
    print(f"TOTAL  v01:{total.v01}  stroke:{total.stroke}  size→sizing:{total.size}  grad:{total.grad}  alias:{total.alias}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
