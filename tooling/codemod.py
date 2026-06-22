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
sys.path.insert(0, os.path.normpath(os.path.join(HERE, "..", "models")))
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
        self.stroke = self.size = self.grad = self.alias = 0


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


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("documents", nargs="+")
    ap.add_argument("--in-place", action="store_true")
    ap.add_argument("--normalize-aliases", action="store_true",
                    help="also rewrite circle/polygon/curve to ellipse/polyline/path")
    ap.add_argument("--bump", action="store_true", help=f"set version to {HEAD_VERSION}")
    args = ap.parse_args(argv)

    total = Stats()
    for path in args.documents:
        doc = yaml.safe_load(open(path, encoding="utf-8"))
        st = Stats()
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
              f"(stroke:{st.stroke} size→sizing:{st.size} grad:{st.grad} alias:{st.alias})")
        for f in ("stroke", "size", "grad", "alias"):
            setattr(total, f, getattr(total, f) + getattr(st, f))
    print(f"TOTAL  stroke:{total.stroke}  size→sizing:{total.size}  grad:{total.grad}  alias:{total.alias}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
