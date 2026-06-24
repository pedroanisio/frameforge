#!/usr/bin/env python3
"""
validate.py — the FrameGraph v2 HEAD validator.

Two layers, in this order:

  1. STRUCTURE — validate the document against models/framegraph.py (the closed
     core profile). Out-of-profile object/flow types (the UML zoo, charts,
     components, ontology) are reported as WARNINGS, not errors — the §8.5
     conformance mechanism — so an extended document still passes with a notice.

  2. STATIC / SEMANTIC / GEOMETRIC RULES that a JSON Schema cannot express
     (complement recommendations #4, #6, #7, #8 + Patch 3 §3.3 audit):
        E stroke single-form (P3)            E hug on a pure shape (P4)
        E legacy `size` → `sizing` (P4)       E fill/fr under `free` (P4)
        E box-less primitive under row/col/grid (P3 §3.6f)
        E content-sized text needs a pinned font (P4 Part C)
        W grid_span bounds / non-grid parent  W deprecated alias types
        W geometric audit: containment, free-group overlap, tabular box-model mandate

Exit code: 0 if no errors (warnings allowed), 1 if any error, 2 on load failure.

Usage:
    python3 validate.py doc.fg.yaml [doc2 ...] [--strict] [--quiet]
      --strict : treat warnings as errors (and reject out-of-profile types)
"""
from __future__ import annotations

import argparse
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.normpath(os.path.join(HERE, "..", "models")))

import yaml  # noqa: E402
import framegraph as fg  # noqa: E402
from pydantic import ValidationError  # noqa: E402

_YAML_LOADER = getattr(yaml, "CSafeLoader", yaml.SafeLoader)

CORE_OBJECT_TYPES = {
    "rect", "ellipse", "circle", "line", "polyline", "polygon", "path", "curve",
    "bezier", "text", "image", "icon", "bullet_list", "dimension", "table", "group",
}
CORE_FLOW_TYPES = {
    "paragraph", "heading", "list", "spacer", "page_break", "column_break", "table",
    "image", "figure", "block", "keep_together", "code", "math", "toc", "bibliography",
}
PURE_SHAPES = {"rect", "ellipse", "circle", "line", "polyline", "polygon", "path", "curve", "bezier"}
BOXLESS = {"line", "ellipse", "polyline", "path", "curve", "bezier"}
DEPRECATED_ALIASES = {"circle", "polygon", "curve", "bezier"}


class Finding:
    __slots__ = ("severity", "code", "msg", "path")

    def __init__(self, severity, code, msg, path):
        self.severity, self.code, self.msg, self.path = severity, code, msg, path

    def __str__(self):
        return f"  [{self.severity}] {self.code} @ {self.path}: {self.msg}"


# --------------------------------------------------------------------------- #
def _load(path):
    with open(path, encoding="utf-8") as fh:
        try:
            return yaml.load(fh, Loader=_YAML_LOADER)
        except yaml.YAMLError:
            if _YAML_LOADER is yaml.SafeLoader:
                raise
            fh.seek(0)
            return yaml.load(fh, Loader=yaml.SafeLoader)


def _num(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def _canvas_wh(canvas):
    presets = {
        "A4": (595, 842), "A3": (842, 1191), "A5": (419.5, 595.3), "Letter": (612, 792),
        "Legal": (612, 1008), "Tabloid": (792, 1224), "deck-16x9": (1920, 1080),
        "deck-4x3": (1024, 768), "square": (1080, 1080), "phone": (390, 844),
        "tablet": (834, 1112), "web": (1280, 800),
    }
    if isinstance(canvas, str):
        return presets.get(canvas)
    if isinstance(canvas, dict):
        if canvas.get("size"):
            s = canvas["size"]
            return (s[0], s[1])
        if canvas.get("preset"):
            return presets.get(canvas["preset"])
    return None


# ---- structural validation with profile awareness ------------------------- #
def structural(doc, findings):
    try:
        fg.Document.model_validate(doc)
        return
    except ValidationError as e:
        for err in e.errors():
            loc = ".".join(str(p) for p in err["loc"])
            if err["type"] in ("union_tag_invalid", "literal_error") and "type" in err["loc"]:
                findings.append(Finding("WARN", "out-of-profile",
                                        f"object/flow type not in the HEAD core profile "
                                        f"({err.get('input')!r}); validated loosely", loc))
            elif err["type"] == "union_tag_invalid":
                findings.append(Finding("WARN", "out-of-profile",
                                        f"discriminated type not in the core profile; "
                                        f"validated loosely", loc))
            elif "paint-only (P3)" in err["msg"] or "paint-only at HEAD (P3)" in err["msg"]:
                continue  # the dedicated R1 stroke-single-form rule reports this
            else:
                findings.append(Finding("ERROR", "structure", err["msg"], loc))


# ---- tree walkers --------------------------------------------------------- #
def walk_objects(node, path, parent_layout, sink):
    """Yield (obj, path, parent_layout_kind) for every visual object."""
    if isinstance(node, dict) and node.get("type"):
        sink.append((node, path, parent_layout))
        if node.get("type") == "group":
            lk = (node.get("layout") or {}).get("kind", "free")
            for i, ch in enumerate(node.get("children", []) or []):
                walk_objects(ch, f"{path}.children[{i}]", lk, sink)


def collect_pages(doc):
    return doc.get("pages", []) if isinstance(doc, dict) else []


def collect_fonts(doc):
    return (((doc.get("defs") or {}).get("tokens") or {}).get("fonts") or {})


def collect_styles(doc):
    return (((doc.get("defs") or {}).get("tokens") or {}).get("text_styles") or {})


# ---- semantic / static rules ---------------------------------------------- #
def rule_checks(doc, findings):
    fonts = collect_fonts(doc)
    styles = collect_styles(doc)

    def font_pinned(font_ref):
        fd = fonts.get(font_ref)
        if isinstance(fd, dict):
            return bool(fd.get("src") and fd.get("hash"))
        return False  # bare-string font or unknown ⇒ not pinned

    def style_font(style_ref):
        sd = style_ref if isinstance(style_ref, dict) else styles.get(style_ref, {})
        if isinstance(sd, dict):
            return sd.get("font_family") or sd.get("font")
        return None

    objs = []
    for pi, page in enumerate(collect_pages(doc)):
        if not isinstance(page, dict):
            continue
        layers = page.get("layers") or []
        for li, layer in enumerate(layers):
            for oi, o in enumerate(layer.get("objects", []) or []):
                walk_objects(o, f"pages[{pi}].layers[{li}].objects[{oi}]", "free", objs)
        # also masters' fixed + running, figures in story, etc. (kept shallow)
    # flows
    for pi, page in enumerate(collect_pages(doc)):
        if isinstance(page, dict) and page.get("mode") == "flow":
            for si, fl in enumerate(page.get("story", []) or []):
                _walk_flow(fl, f"pages[{pi}].story[{si}]", objs)

    for o, path, parent_layout in objs:
        t = o.get("type")
        sizing = o.get("sizing") or {}
        # R1 stroke single-form (P3)
        stroke_value = o.get("stroke")
        if isinstance(stroke_value, dict) and any(
            k in stroke_value for k in ("width", "dash", "linecap", "linejoin")
        ):
            findings.append(Finding("ERROR", "stroke-single-form",
                                    "inline-geometry `stroke` removed in P3; use paint in `stroke` "
                                    "+ geometry in `stroke_style` (codemod)", path))
        # R2 legacy `size` on a non-icon object
        if t != "icon" and "size" in o:
            findings.append(Finding("ERROR", "size-renamed",
                                    "`size` collides with IconObject.size; the content-sizing key is "
                                    "`sizing` at HEAD (codemod)", path))
        # R3 hug on a pure shape
        if t in PURE_SHAPES and (sizing.get("width") == "hug" or sizing.get("height") == "hug"):
            findings.append(Finding("ERROR", "hug-on-shape",
                                    f"`hug` is invalid on {t!r} (no intrinsic content); use fixed/fill", path))
        # R4 fill / fr under free
        if parent_layout in (None, "free"):
            if sizing.get("width") == "fill" or sizing.get("height") == "fill":
                findings.append(Finding("ERROR", "fill-under-free",
                                        "`fill` has no main axis under `free` (or absent layout)", path))
            box = o.get("box") or []
            for d in box[2:4]:
                if isinstance(d, str) and d.strip().endswith("fr"):
                    findings.append(Finding("ERROR", "fr-under-free",
                                            "`fr` box dimension is only valid inside a layout container", path))
        # R5 grid_span
        if "grid_span" in o:
            if parent_layout != "grid":
                findings.append(Finding("WARN", "grid_span-parent",
                                        "`grid_span` only applies under a `grid` layout parent", path))
        # R6 box-less primitive directly under layout containers
        if parent_layout in ("row", "column", "grid", "wrap") and t in BOXLESS and not o.get("box"):
            findings.append(Finding("ERROR", "boxless-under-layout",
                                    f"box-less {t!r} cannot be a direct {parent_layout} child "
                                    "(no extent to advance by); wrap in a group or give a box", path))
        # R7 content-sized text needs a pinned font
        if t == "text" and (sizing.get("width") in ("hug", "fill") or sizing.get("height") in ("hug", "fill")):
            fref = style_font(o.get("style"))
            if not fref or not font_pinned(fref):
                findings.append(Finding("ERROR", "unpinned-font",
                                        "content-sized text must reference a pinned font "
                                        "(tokens.fonts entry with both `src` and `hash`) — §9.6/P4", path))
        # R10 deprecated alias types
        if t in DEPRECATED_ALIASES:
            findings.append(Finding("WARN", "deprecated-alias",
                                    f"{t!r} is a renderer-shortcut alias; codemod normalises it "
                                    f"({'ellipse' if t=='circle' else 'closed polyline' if t=='polygon' else 'path'})",
                                    path))

    # R8 geometric audit (box-based, page space) + tabular signature
    _geometric_audit(doc, findings)
    _free_group_overlap(doc, findings)
    # R9b out-of-profile defs keys (grammar-allowed, out of deep core profile)
    defs = doc.get("defs") or {}
    for k in ("symbols", "components", "ontology"):
        if k in defs:
            findings.append(Finding("WARN", "out-of-profile",
                                    f"`defs.{k}` is out of the HEAD core profile; accepted but not "
                                    "deeply validated (§8.5 conformance)", f"defs.{k}"))
    # R10b deprecated top-level text_contract
    if isinstance(doc, dict) and "text_contract" in doc:
        findings.append(Finding("WARN", "text_contract-placement",
                                "top-level `text_contract` is a renderer convenience; the normative home "
                                "is a master/page RenderingContract.text", "text_contract"))


def _free_group_overlap(doc, findings):
    """§3.3 scoped non-overlap: only within a `free`-layout group or a cluster
    marked `meta.no_overlap: true`. Global/layer overlap stays legal (z-order)."""
    def check_children(children, path):
        boxes = []
        for i, ch in enumerate(children or []):
            if isinstance(ch, dict) and ch.get("box") and all(_num(v) for v in ch["box"]) \
                    and not ch.get("decorative"):
                boxes.append((f"{path}.children[{i}]", *ch["box"]))
        for a in range(len(boxes)):
            for b in range(a + 1, len(boxes)):
                pa, ax, ay, aw, ah = boxes[a]
                _, bx, by, bw, bh = boxes[b]
                ox = max(0, min(ax + aw, bx + bw) - max(ax, bx))
                oy = max(0, min(ay + ah, by + bh) - max(ay, by))
                area = ox * oy
                if area > 0.1 * min(aw * ah, bw * bh) and area > 100:
                    findings.append(Finding("WARN", "overlap",
                                            f"boxes overlap by ~{area:.0f} px² inside a no-overlap "
                                            "scope (free group / meta.no_overlap)", pa))
                    break

    def walk(node, path):
        if isinstance(node, list):
            for i, x in enumerate(node):
                walk(x, f"{path}[{i}]")
        elif isinstance(node, dict):
            if node.get("type") == "group":
                lk = (node.get("layout") or {}).get("kind", "free")
                no_overlap = (node.get("meta") or {}).get("no_overlap") is True
                if lk == "free" or no_overlap:
                    check_children(node.get("children"), path)
            for k, v in node.items():
                walk(v, f"{path}.{k}")

    walk(doc.get("pages", []), "pages")


def _walk_flow(fl, path, objs):
    if not isinstance(fl, dict):
        return
    if fl.get("type") == "figure" and isinstance(fl.get("object"), dict):
        walk_objects(fl["object"], f"{path}.object", "free", objs)
    for key in ("children", "content"):
        for i, ch in enumerate(fl.get(key, []) or []):
            _walk_flow(ch, f"{path}.{key}[{i}]", objs)


def _geometric_audit(doc, findings):
    for pi, page in enumerate(collect_pages(doc)):
        if not isinstance(page, dict) or page.get("mode") != "page":
            continue
        wh = _canvas_wh(page.get("canvas")) or _canvas_wh("A4")
        if not wh:
            continue
        cw, ch = wh
        for li, layer in enumerate(page.get("layers", []) or []):
            boxed_text = []
            for oi, o in enumerate(layer.get("objects", []) or []):
                if not isinstance(o, dict):
                    continue
                box = o.get("box")
                p = f"pages[{pi}].layers[{li}].objects[{oi}]"
                if box and all(_num(v) for v in box):
                    x, y, w, h = box
                    # containment (SHOULD): object within canvas + small tolerance
                    if not o.get("decorative") and (x < -1 or y < -1 or x + w > cw + 1 or y + h > ch + 1):
                        findings.append(Finding("WARN", "containment",
                                                f"object box extends outside the {cw:g}×{ch:g} canvas", p))
                    if o.get("type") == "text" and (o.get("meta") or {}).get("role") != "lettering":
                        boxed_text.append((x, y, w, h))
            # NOTE: layer-level overlap is NOT flagged — global overlap is legal
            # (z-order is intentional, §3.3). Overlap is only checked inside `free`
            # groups / `meta.no_overlap` clusters (see _free_group_overlap).
            # tabular box-model mandate: ≥6 absolutely-placed text in a regular grid
            if len(boxed_text) >= 6:
                xs = sorted({round(b[0]) for b in boxed_text})
                ys = sorted({round(b[1]) for b in boxed_text})
                if len(xs) >= 2 and len(ys) >= 3 and len(xs) * len(ys) >= len(boxed_text):
                    findings.append(Finding("WARN", "tabular-box-model",
                                            f"{len(boxed_text)} absolutely-positioned text objects form an "
                                            "approximately regular grid; author as a row/column/grid group "
                                            "or a TableObject (§3.3)", f"pages[{pi}].layers[{li}]"))


# --------------------------------------------------------------------------- #
def validate_doc(path, strict=False):
    try:
        doc = _load(path)
    except Exception as exc:  # noqa: BLE001
        return None, [Finding("ERROR", "load", f"could not parse: {exc}", path)], 2
    findings: list[Finding] = []
    structural(doc, findings)
    rule_checks(doc, findings)
    if strict:
        for f in findings:
            if f.severity == "WARN":
                f.severity = "ERROR"
    errs = sum(1 for f in findings if f.severity == "ERROR")
    return doc, findings, (1 if errs else 0)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("documents", nargs="+")
    ap.add_argument("--strict", action="store_true", help="treat warnings as errors")
    ap.add_argument("--quiet", action="store_true", help="only print summary lines")
    args = ap.parse_args(argv)

    rc = 0
    for path in args.documents:
        _, findings, code = validate_doc(path, strict=args.strict)
        rc = max(rc, code)
        e = sum(1 for f in findings if f.severity == "ERROR")
        w = sum(1 for f in findings if f.severity == "WARN")
        status = "FAIL" if e else ("WARN" if w else "PASS")
        print(f"{status}  {os.path.basename(path)}  ({e} error(s), {w} warning(s))")
        if not args.quiet:
            for f in findings:
                print(f)
    return rc


if __name__ == "__main__":
    sys.exit(main())
