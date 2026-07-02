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
        E referential integrity (R12, §3.1/§3.3): dangling anchor/use refs,
          unknown style/stroke_style/text_style tokens, unknown masters/regions
        W unknown colour-ish tokens, icon fonts, adjustment hide targets (R12)
        W grid_span bounds / non-grid parent  W deprecated alias types
        W geometric audit: containment, free-group overlap, tabular box-model mandate

The per-object rules walk page layers, flow figures, AND defs.masters' fixed +
running objects (the render surface). The geometric audit resolves each page's
canvas the way the renderer does: page canvas → master canvas → the renderer
default; preset sizes are sourced from the renderer's CanvasResolver.PRESETS
(AST-parsed, so the two tables cannot drift).

Exit code: 0 if no errors (warnings allowed), 1 if any error, 2 on load failure.

Usage:
    python3 validate.py doc.fg.yaml [doc2 ...] [--strict] [--quiet]
      --strict : treat warnings as errors (and reject out-of-profile types)
"""
from __future__ import annotations

import argparse
import ast
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.normpath(os.path.join(HERE, "..", "docs", "models")))

import yaml  # noqa: E402
import framegraph as fg  # noqa: E402
from pydantic import ValidationError  # noqa: E402

_YAML_LOADER = getattr(yaml, "CSafeLoader", yaml.SafeLoader)

CORE_OBJECT_TYPES = {
    "rect", "ellipse", "circle", "line", "polyline", "polygon", "path", "curve",
    "bezier", "text", "image", "icon", "bullet_list", "dimension", "connector",
    "table", "group",
}
CORE_FLOW_TYPES = {
    "paragraph", "heading", "list", "spacer", "page_break", "column_break", "table",
    "image", "figure", "block", "keep_together", "code", "math", "toc", "bibliography",
}
PURE_SHAPES = {"rect", "ellipse", "circle", "line", "polyline", "polygon", "path", "curve", "bezier"}
BOXLESS = {"line", "ellipse", "polyline", "path", "curve", "bezier"}
DEPRECATED_ALIASES = {"circle", "polygon", "curve", "bezier"}

# --------------------------------------------------------------------------- #
#  Canvas presets — sourced from the renderer (single pixel source, spec §4)  #
# --------------------------------------------------------------------------- #
_CANVAS_RESOLVER_SRC = os.path.normpath(os.path.join(
    HERE, "..", "framegraph", "rendering", "domain", "services", "canvas_resolver.py"))
# Standalone fallback (validate.py must not import the `framegraph` rendering
# package — it would shadow the models module). Kept an exact copy of
# CanvasResolver.PRESETS/DEFAULT_WH; tests/test_validate.py gates the equality.
_FALLBACK_PRESETS = {
    "A3": (842, 1191), "A4": (595, 842), "A5": (419.5, 595.3), "Letter": (612, 792),
    "Legal": (612, 1008), "Tabloid": (792, 1224),
    "deck-16x9": (1920, 1080), "deck-4x3": (1024, 768), "square": (1080, 1080),
    "phone": (390, 844), "tablet": (834, 1112), "web": (1280, 800),
    "instagram-square": (1080, 1080), "instagram-portrait": (1080, 1350),
    "instagram-landscape": (1080, 566), "instagram-story": (1080, 1920),
    "facebook-post": (1200, 630), "facebook-cover": (820, 312),
    "facebook-story": (1080, 1920),
    "twitter-post": (1600, 900), "twitter-header": (1500, 500),
    "linkedin-post": (1200, 627), "linkedin-cover": (1584, 396),
    "youtube-thumbnail": (1280, 720), "youtube-banner": (2560, 1440),
    "tiktok-video": (1080, 1920), "pinterest-pin": (1000, 1500),
    "snapchat": (1080, 1920), "story": (1080, 1920),
    "1x1": (1080, 1080), "4x5": (1080, 1350), "5x4": (1350, 1080),
    "9x16": (1080, 1920), "16x9": (1920, 1080), "2x3": (1080, 1620),
    "3x2": (1620, 1080), "1.91x1": (1200, 628), "3x1": (1500, 500),
    "book-pocket": (288, 432), "book-mass-market": (306, 494.6),
    "book-trade": (360, 576), "book-novel": (378, 576), "book-digest": (396, 612),
    "book-6x9": (432, 648), "book-7x10": (504, 720), "book-8x10": (576, 720),
    "book-textbook": (612, 792), "book-square-8": (576, 576),
    "book-picture": (612, 612), "book-square-10": (720, 720),
    "book-coffee-table": (648, 864), "book-art-10x12": (720, 864),
    "book-art-11x14": (792, 1008),
}
_FALLBACK_DEFAULT_WH = (1280, 800)


def _load_renderer_presets():
    """PRESETS/DEFAULT_WH read from the renderer's CanvasResolver source by AST
    parse — the same table the render pass uses, without importing the package."""
    try:
        tree = ast.parse(open(_CANVAS_RESOLVER_SRC, encoding="utf-8").read())
        presets = default = None
        for node in tree.body:
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if getattr(target, "id", None) == "PRESETS":
                        presets = ast.literal_eval(node.value)
                    elif getattr(target, "id", None) == "DEFAULT_WH":
                        default = tuple(ast.literal_eval(node.value))
        if presets and default:
            return presets, default
    except (OSError, SyntaxError, ValueError):
        pass
    return dict(_FALLBACK_PRESETS), _FALLBACK_DEFAULT_WH


PRESETS, DEFAULT_WH = _load_renderer_presets()

# CSS Color Module Level 4 §6.1 named colors (147 X11 keywords + rebeccapurple).
CSS_COLOR_NAMES = frozenset("""
aliceblue antiquewhite aqua aquamarine azure beige bisque black blanchedalmond
blue blueviolet brown burlywood cadetblue chartreuse chocolate coral
cornflowerblue cornsilk crimson cyan darkblue darkcyan darkgoldenrod darkgray
darkgreen darkgrey darkkhaki darkmagenta darkolivegreen darkorange darkorchid
darkred darksalmon darkseagreen darkslateblue darkslategray darkslategrey
darkturquoise darkviolet deeppink deepskyblue dimgray dimgrey dodgerblue
firebrick floralwhite forestgreen fuchsia gainsboro ghostwhite gold goldenrod
gray green greenyellow grey honeydew hotpink indianred indigo ivory khaki
lavender lavenderblush lawngreen lemonchiffon lightblue lightcoral lightcyan
lightgoldenrodyellow lightgray lightgreen lightgrey lightpink lightsalmon
lightseagreen lightskyblue lightslategray lightslategrey lightsteelblue
lightyellow lime limegreen linen magenta maroon mediumaquamarine mediumblue
mediumorchid mediumpurple mediumseagreen mediumslateblue mediumspringgreen
mediumturquoise mediumvioletred midnightblue mintcream mistyrose moccasin
navajowhite navy oldlace olive olivedrab orange orangered orchid palegoldenrod
palegreen paleturquoise palevioletred papayawhip peachpuff peru pink plum
powderblue purple rebeccapurple red rosybrown royalblue saddlebrown salmon
sandybrown seagreen seashell sienna silver skyblue slateblue slategray
slategrey snow springgreen steelblue tan teal thistle tomato turquoise violet
wheat white whitesmoke yellow yellowgreen
""".split())
_COLOR_FN_RE = re.compile(r"^(?:rgb|rgba|hsl|hsla|hwb|lab|lch|oklab|oklch|color)\(", re.IGNORECASE)
_CSS_WIDE_KEYWORDS = {"inherit", "initial", "unset", "revert"}


def _is_color_literal(s):
    """A string the renderer/SVG can take without token resolution."""
    low = s.strip().lower()
    return (low.startswith("#") or low.startswith("url(")
            or low in ("none", "transparent", "currentcolor")
            or low in _CSS_WIDE_KEYWORDS
            or bool(_COLOR_FN_RE.match(low))
            or low in CSS_COLOR_NAMES)


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
    if isinstance(canvas, str):
        return PRESETS.get(canvas)
    if isinstance(canvas, dict):
        if canvas.get("size"):
            s = canvas["size"]
            return (s[0], s[1])
        if canvas.get("preset"):
            return PRESETS.get(canvas["preset"])
    return None


def _page_canvas_wh(doc, page):
    """Resolve a page's canvas the way the renderer's CanvasResolver does:
    page canvas → its master's canvas → DEFAULT_WH. Returns (wh, declared):
    wh is None only when a canvas IS declared but cannot be resolved."""
    canvas = page.get("canvas")
    if canvas is None and page.get("master"):
        masters = (doc.get("defs") or {}).get("masters") or {}
        master = masters.get(page.get("master"))
        if isinstance(master, dict):
            canvas = master.get("canvas")
    if canvas is None:
        return DEFAULT_WH, None
    return _canvas_wh(canvas), canvas


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
                                        "discriminated type not in the core profile; "
                                        "validated loosely", loc))
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
    # masters' fixed + running objects are render surface too — same rules apply
    for mname, master, mobjs in _master_object_lists(doc):
        for slot, lst in mobjs:
            for oi, o in enumerate(lst):
                walk_objects(o, f"defs.masters.{mname}.{slot}[{oi}]", "free", objs)
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
        # R11 non-conformant 3D (G-2): `perspective` is declared but no render
        # target applies a 3D perspective — it passes through inert, a "declared,
        # may not render" trap. Flag it (WARN, not ERROR — the doc is still valid);
        # author 3D via the SDK Scene3D 2D-projection (Appendix A.5) instead.
        st = o.get("style")
        if isinstance(st, dict) and st.get("perspective") not in (None, "none"):
            findings.append(Finding("WARN", "non-conformant-3d",
                                    "`perspective` is non-conformant: no render target applies a 3D "
                                    "perspective; it passes through inert. Author 3D via the SDK "
                                    "Scene3D projection (Appendix A.5).", f"{path}.style.perspective"))

    # R8 geometric audit (box-based, page space) + tabular signature
    _geometric_audit(doc, findings)
    _free_group_overlap(doc, findings)
    # R12 referential integrity (§3.1/§3.3): ids, tokens, masters, adjustments
    _ref_integrity(doc, findings)
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


def _master_object_lists(doc):
    """Yield (master_name, master_dict, [(slot_path, objects), ...]) for every
    defs.masters entry carrying visual objects (fixed + running header/footer)."""
    masters = (doc.get("defs") or {}).get("masters") or {}
    for mname, master in masters.items():
        if not isinstance(master, dict):
            continue
        lists = []
        if isinstance(master.get("fixed"), list):
            lists.append(("fixed", master["fixed"]))
        running = master.get("running") or {}
        if isinstance(running, dict):
            for slot in ("header", "footer"):
                if isinstance(running.get(slot), list):
                    lists.append((f"running.{slot}", running[slot]))
        yield mname, master, lists


# ---- R12 referential integrity (§3.1/§3.3) --------------------------------- #
# Keys whose values are free-form bags: never token/id namespaces, so the
# reference walk must not descend into them (meta may legally contain anything).
_OPAQUE_KEYS = {"meta", "semantic", "semantics", "typography", "data",
                "page_numbering", "ontology", "symbols", "components", "css"}


def _collect_ids(objects):
    """Object ids reachable the way the renderer indexes them (groups' children)."""
    ids = set()

    def visit(o):
        if not isinstance(o, dict):
            return
        if isinstance(o.get("id"), str):
            ids.add(o["id"])
        for ch in o.get("children") or []:
            visit(ch)

    for o in objects or []:
        visit(o)
    return ids


def _near(name, candidates, n=4):
    """Short hint list of declared candidates for an unresolved reference."""
    cands = sorted(candidates)
    if not cands:
        return "none declared"
    pre = [c for c in cands if c[:2] == str(name)[:2]] or cands
    shown = ", ".join(pre[:n])
    return f"declared: {shown}" + (", …" if len(cands) > n else "")


def _ref_integrity(doc, findings):
    if not isinstance(doc, dict):
        return
    defs = doc.get("defs") or {}
    tokens = defs.get("tokens") or {}
    styles_ns = set(tokens.get("styles") or {}) | set(tokens.get("text_styles") or {})
    stroke_ns = set(tokens.get("stroke_styles") or {})
    color_ns = set(tokens.get("colors") or {})
    fill_ns = color_ns | set(tokens.get("fill_styles") or {})
    font_ns = set(tokens.get("fonts") or {})
    master_ns = set(defs.get("masters") or {})
    symbol_ns = set(defs.get("symbols") or {})

    def err(code, msg, path, warn=False):
        findings.append(Finding("WARN" if warn else "ERROR", code, msg, path))

    # --- anchors (connector endpoints, line/dimension anchor objects), use --- #
    def check_anchor(a, ids, path):
        ref = None
        if isinstance(a, dict):
            ref = a.get("ref") or a.get("object")
        elif isinstance(a, str):
            ref = a
        if isinstance(ref, str) and ref not in ids:
            err("dangling-ref",
                f"anchor references object id {ref!r} which is not declared on this "
                f"page/master ({_near(ref, ids)})", path)

    def check_scope_objects(objects, base_path, ids):
        scoped = []
        for oi, o in enumerate(objects or []):
            walk_objects(o, f"{base_path}[{oi}]", "free", scoped)
        for o, path, _pl in scoped:
            t = o.get("type")
            if t in ("connector", "line", "dimension", "curve", "bezier"):
                check_anchor(o.get("from"), ids, f"{path}.from")
                check_anchor(o.get("to"), ids, f"{path}.to")
            if t == "use":
                sym = o.get("symbol")
                if isinstance(sym, str) and sym not in symbol_ns:
                    err("dangling-ref",
                        f"`use` references symbol {sym!r} not declared in defs.symbols "
                        f"({_near(sym, symbol_ns)}); it would expand to an empty group", path)

    for pi, page in enumerate(collect_pages(doc)):
        if not isinstance(page, dict):
            continue
        page_objs = [o for layer in page.get("layers") or []
                     for o in (layer.get("objects") or [])]
        ids = _collect_ids(page_objs)
        for li, layer in enumerate(page.get("layers") or []):
            check_scope_objects(layer.get("objects"), f"pages[{pi}].layers[{li}].objects", ids)
    for mname, master, mobjs in _master_object_lists(doc):
        all_master_objs = [o for _slot, lst in mobjs for o in lst]
        ids = _collect_ids(all_master_objs)
        for slot, lst in mobjs:
            check_scope_objects(lst, f"defs.masters.{mname}.{slot}", ids)

    # --- masters + region chains --------------------------------------------- #
    for pi, page in enumerate(collect_pages(doc)):
        if isinstance(page, dict) and isinstance(page.get("master"), str) \
                and page["master"] not in master_ns:
            err("unknown-master",
                f"references master {page['master']!r} not declared in defs.masters "
                f"({_near(page['master'], master_ns)})", f"pages[{pi}].master")
    for mname, master, _mobjs in _master_object_lists(doc):
        nxt = master.get("next")
        if isinstance(nxt, str) and nxt not in master_ns:
            err("unknown-master",
                f"continuation master {nxt!r} not declared in defs.masters "
                f"({_near(nxt, master_ns)})", f"defs.masters.{mname}.next")
        regions = [r for r in (master.get("regions") or []) if isinstance(r, dict)]
        region_ids = {r["id"] for r in regions if isinstance(r.get("id"), str)}
        for ri, r in enumerate(regions):
            rn = r.get("next")
            if isinstance(rn, str) and rn not in region_ids:
                err("dangling-ref",
                    f"region `next` {rn!r} does not name a region of this master "
                    f"({_near(rn, region_ids)})", f"defs.masters.{mname}.regions[{ri}].next")

    # --- adjustments hide targets (advisory: hiding nothing is inert) --------- #
    all_ids = set()
    for page in collect_pages(doc):
        if isinstance(page, dict):
            all_ids |= _collect_ids([o for layer in page.get("layers") or []
                                     for o in (layer.get("objects") or [])])
    for _mname, _master, mobjs in _master_object_lists(doc):
        all_ids |= _collect_ids([o for _slot, lst in mobjs for o in lst])
    for ti, target in enumerate(doc.get("targets") or []):
        if not isinstance(target, dict):
            continue
        hide = (target.get("adjustments") or {}).get("hide") or []
        for hi, hid in enumerate(hide):
            if isinstance(hid, str) and hid not in all_ids:
                err("unknown-adjustment-target",
                    f"adjustments.hide names id {hid!r} which no object declares "
                    f"({_near(hid, all_ids)})", f"targets[{ti}].adjustments.hide[{hi}]",
                    warn=True)

    # --- token references (style/stroke_style/text_style/class + colours) ----- #
    def is_styled_carrier(d):
        # a dict whose `style` is a token ref (objects/flowables/spans/cells) —
        # NOT BorderSide/TextDecoration/FontDef, whose `style` is a CSS keyword.
        return any(k in d for k in ("type", "kind", "text", "spans", "content"))

    def walk_tokens(node, path):
        if isinstance(node, list):
            for i, x in enumerate(node):
                walk_tokens(x, f"{path}[{i}]")
            return
        if not isinstance(node, dict):
            return
        st = node.get("style")
        if isinstance(st, str) and is_styled_carrier(node) and st not in styles_ns:
            err("unknown-token",
                f"style token {st!r} is not declared in tokens.styles/text_styles "
                f"({_near(st, styles_ns)}); the renderer silently applies no style",
                f"{path}.style")
        ss = node.get("stroke_style")
        if isinstance(ss, str) and ss not in stroke_ns:
            err("unknown-token",
                f"stroke_style token {ss!r} is not declared in tokens.stroke_styles "
                f"({_near(ss, stroke_ns)})", f"{path}.stroke_style")
        ts = node.get("text_style")
        if isinstance(ts, str) and ts not in styles_ns:
            err("unknown-token",
                f"text_style token {ts!r} is not declared in tokens.text_styles/styles "
                f"({_near(ts, styles_ns)})", f"{path}.text_style")
        cls = node.get("class")
        for c in ([cls] if isinstance(cls, str) else (cls if isinstance(cls, list) else [])):
            if isinstance(c, str) and c not in styles_ns:
                err("unknown-token",
                    f"style class {c!r} is not declared in tokens.styles/text_styles "
                    f"({_near(c, styles_ns)})", f"{path}.class")
        for key in ("fill", "stroke", "color", "background_color", "marker_color", "header_fill"):
            v = node.get(key)
            if isinstance(v, str) and v not in fill_ns and not _is_color_literal(v):
                err("unknown-token",
                    f"{key} value {v!r} is neither a colour literal nor a declared "
                    f"tokens.colors{'/fill_styles' if key in ('fill', 'stroke') else ''} "
                    f"key ({_near(v, fill_ns)}); it would pass through as an invalid "
                    f"SVG colour", f"{path}.{key}", warn=True)
        if node.get("type") == "icon":
            fnt = node.get("font")
            if isinstance(fnt, str) and fnt not in font_ns:
                err("unknown-token",
                    f"icon font {fnt!r} is not declared in tokens.fonts "
                    f"({_near(fnt, font_ns)}) — §3.5 resolves icon fonts against tokens",
                    f"{path}.font", warn=True)
        for k, v in node.items():
            if k in _OPAQUE_KEYS:
                continue
            walk_tokens(v, f"{path}.{k}")

    walk_tokens(doc.get("pages"), "pages")
    walk_tokens((defs.get("masters") or {}), "defs.masters")
    for ns in ("styles", "text_styles", "stroke_styles"):
        walk_tokens(tokens.get(ns) or {}, f"defs.tokens.{ns}")


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
        wh, declared = _page_canvas_wh(doc, page)
        if wh is None:
            findings.append(Finding("WARN", "canvas-unresolved",
                                    f"canvas {declared!r} does not resolve to a known preset/size; "
                                    "containment audit skipped for this page", f"pages[{pi}].canvas"))
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
            # tabular box-model mandate: ≥6 absolutely-placed text in a regular grid.
            # A real table REUSES column/row positions: ≥2 columns each with stacked
            # cells AND ≥3 rows each with side-by-side cells, with ≥6 cells on that
            # grid. Scattered (free-placed) text has unique x/y per object, so it
            # forms no shared columns/rows and is not flagged (avoids false positives
            # on covers, contact pages, and other non-tabular layouts).
            if len(boxed_text) >= 6:
                xcount: dict[int, int] = {}
                ycount: dict[int, int] = {}
                for bx, by, _bw, _bh in boxed_text:
                    xcount[round(bx)] = xcount.get(round(bx), 0) + 1
                    ycount[round(by)] = ycount.get(round(by), 0) + 1
                cols = {x for x, n in xcount.items() if n >= 2}
                rows = {y for y, n in ycount.items() if n >= 2}
                cells = sum(1 for bx, by, _bw, _bh in boxed_text
                            if round(bx) in cols and round(by) in rows)
                if len(cols) >= 2 and len(rows) >= 3 and cells >= 6:
                    findings.append(Finding("WARN", "tabular-box-model",
                                            f"{cells} absolutely-positioned text objects form an "
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
