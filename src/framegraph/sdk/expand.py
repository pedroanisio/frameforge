"""Expansion helpers for deterministic FrameGraph documents."""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import copy
import os
from pathlib import Path
import re
from typing import Any

from framegraph.sdk.humanize import apply_humanize
from framegraph.sdk.model import validate_document


@dataclass(frozen=True)
class ExpandOptions:
    """Options for SDK expansion."""

    base_dir: str | os.PathLike[str] | None = None
    pin_assets: bool = True
    humanize: bool = True
    """Honor a document/object ``humanize`` spec. Set False to force the seeded
    imperfection pass off — required for measurement/fidelity renders (vision,
    ``score_reconstruction``) so perturbation never poisons a pixel measurement."""


@dataclass(frozen=True)
class ExpandedDocument:
    """Expanded document plus expansion metadata."""

    document: Any
    pinned: tuple[str, ...]


def expand(model: Any, opts: ExpandOptions | None = None) -> ExpandedDocument:
    """Expand deterministic SDK-resolvable pieces and return a validated model.

    Expansion is the compatibility boundary for out-of-core authoring forms. It
    lowers grammar-level ``use`` and simple ``component`` objects into current
    core 2D primitives, pins local asset/font hashes, then validates the result.
    Geometry helpers already emit concrete 2D FrameGraph primitives before
    documents reach this function; unsupported future computed nodes fail
    validation instead of leaking through.
    """
    options = opts or ExpandOptions()
    data = _plain_input(model)
    data = _expand_reuse(data)
    if options.humanize:
        data = apply_humanize(data)
    base = Path(options.base_dir) if options.base_dir is not None else Path.cwd()
    pinned: list[str] = []
    if options.pin_assets:
        _pin_asset_defs(data, base, pinned)
        _pin_font_defs(data, base, pinned)
    expanded = validate_document(data)
    return ExpandedDocument(document=expanded, pinned=tuple(pinned))


def _pin_asset_defs(data: dict[str, Any], base: Path, pinned: list[str]) -> None:
    assets = (((data.get("defs") or {}).get("assets")) or {})
    for name, asset in assets.items():
        if not isinstance(asset, dict) or asset.get("hash"):
            continue
        src = asset.get("src")
        digest = _hash_local_src(src, base)
        if digest:
            asset["hash"] = digest
            pinned.append(f"defs.assets.{name}")


def _pin_font_defs(data: dict[str, Any], base: Path, pinned: list[str]) -> None:
    fonts = ((((data.get("defs") or {}).get("tokens") or {}).get("fonts")) or {})
    for name, font in fonts.items():
        if not isinstance(font, dict) or font.get("hash"):
            continue
        digest = _hash_local_src(font.get("src"), base)
        if digest:
            font["hash"] = digest
            pinned.append(f"defs.tokens.fonts.{name}")


def _hash_local_src(src: object, base: Path) -> str | None:
    if not isinstance(src, str) or _is_remote_or_data(src):
        return None
    path = Path(src)
    if not path.is_absolute():
        path = base / path
    if not path.is_file():
        return None
    return "sha256:" + sha256(path.read_bytes()).hexdigest()


def _is_remote_or_data(src: str) -> bool:
    value = src.strip().lower()
    return value.startswith(("http://", "https://", "data:", "url("))


def _plain_input(model: Any) -> dict[str, Any]:
    if hasattr(model, "model_dump"):
        return model.model_dump(by_alias=True, exclude_none=True)
    if isinstance(model, dict):
        return copy.deepcopy(model)
    return validate_document(model).model_dump(by_alias=True, exclude_none=True)


def _has_expandable(node: Any) -> bool:
    """True if any object in the tree is a self-contained expansion form
    (`graph`) that needs lowering even without defs.symbols/components."""
    if isinstance(node, dict):
        if node.get("type") == "graph":
            return True
        return any(_has_expandable(v) for v in node.values())
    if isinstance(node, list):
        return any(_has_expandable(v) for v in node)
    return False


def _expand_reuse(data: dict[str, Any]) -> dict[str, Any]:
    defs = data.get("defs") if isinstance(data.get("defs"), dict) else {}
    symbols = defs.get("symbols") if isinstance(defs.get("symbols"), dict) else {}
    components = defs.get("components") if isinstance(defs.get("components"), dict) else {}
    if not symbols and not components and not _has_expandable(data.get("pages")):
        return data
    out = copy.deepcopy(data)
    for page in out.get("pages") or []:
        if not isinstance(page, dict):
            continue
        for layer in page.get("layers") or []:
            if isinstance(layer, dict) and isinstance(layer.get("objects"), list):
                layer["objects"] = [_expand_object(obj, symbols, components) for obj in layer["objects"]]
        if isinstance(page.get("story"), list):
            page["story"] = [_expand_flow(flow, symbols, components) for flow in page["story"]]
    return out


def _expand_flow(flow: Any, symbols: dict[str, Any], components: dict[str, Any]) -> Any:
    if not isinstance(flow, dict):
        return flow
    out = copy.deepcopy(flow)
    if isinstance(out.get("object"), dict):
        out["object"] = _expand_object(out["object"], symbols, components)
    for key in ("children", "items"):
        if isinstance(out.get(key), list):
            out[key] = [_expand_flow(item, symbols, components) for item in out[key]]
    return out


def _expand_object(obj: Any, symbols: dict[str, Any], components: dict[str, Any]) -> Any:
    if not isinstance(obj, dict):
        return obj
    kind = obj.get("type")
    if kind == "use":
        return _expand_use(obj, symbols, components)
    if kind == "component":
        return _expand_component(obj, components)
    if kind == "graph":
        return _expand_graph(obj)
    out = copy.deepcopy(obj)
    if isinstance(out.get("children"), list):
        out["children"] = [_expand_object(child, symbols, components) for child in out["children"]]
    return out


def _expand_use(obj: dict[str, Any], symbols: dict[str, Any], components: dict[str, Any]) -> dict[str, Any]:
    symbol_name = obj.get("symbol")
    symbol = symbols.get(symbol_name) if isinstance(symbol_name, str) else None
    if not isinstance(symbol, dict):
        return _invalid_placeholder(obj, "missing-symbol", symbol_name)
    params = obj.get("params") if isinstance(obj.get("params"), dict) else {}
    context = {**params, **{k: v for k, v in obj.items() if k not in {"type", "id", "symbol", "box", "params", "decorative"}}}
    children = [
        _subst(copy.deepcopy(child), context)
        for child in symbol.get("objects", [])
        if isinstance(child, dict)
    ]
    children = [_expand_object(child, symbols, components) for child in children]
    source_box = symbol.get("box") if _is_box(symbol.get("box")) else [0, 0, 1, 1]
    target_box = obj.get("box") if _is_box(obj.get("box")) else source_box
    # Map children into the group's LOCAL frame (origin 0,0), not absolute page
    # coords: a group carrying a `box` is translated to that box origin by the
    # renderer (the same convention Scene3D.render follows — see its regression
    # test), so absolute children here would be offset twice. Scaling still comes
    # from the source→target size ratio.
    local_box = [0.0, 0.0, float(target_box[2]), float(target_box[3])]
    mapped = [_map_object(child, source_box, local_box) for child in children]
    group: dict[str, Any] = {
        "type": "group",
        "box": list(target_box),
        "children": mapped,
        "meta": {"source_symbol": symbol_name},
    }
    for key in ("id", "decorative", "z", "opacity", "style"):
        if key in obj:
            group[key] = obj[key]
    return group


def _expand_component(obj: dict[str, Any], components: dict[str, Any]) -> dict[str, Any]:
    box = obj.get("box") if _is_box(obj.get("box")) else [0, 0, 1, 1]
    spec_name = obj.get("component")
    spec = components.get(spec_name) if isinstance(spec_name, str) else None
    if not isinstance(spec, dict):
        return _invalid_placeholder(obj, "missing-component", spec_name)
    merged = {k: v for k, v in spec.items() if k not in {"variants", "slots"}}
    variants = spec.get("variants") if isinstance(spec.get("variants"), dict) else {}
    variant = variants.get(obj.get("variant"))
    if isinstance(variant, dict):
        merged.update(variant)
    merged.update({k: v for k, v in obj.items() if k not in {"type", "component", "variant", "title", "body"}})
    x, y, w, h = [float(v) for v in box[:4]]
    # Children are LOCAL to the group's box (origin 0,0), mirroring _expand_use:
    # the renderer translates a box-carrying group to its box origin, so
    # absolute children here would be offset twice.
    local_box = [0.0, 0.0, w, h]
    radius = merged.get("radius")
    rect: dict[str, Any] = {
        "type": "rect",
        "box": list(local_box),
        "fill": merged.get("fill", "#fff"),
        "stroke": merged.get("stroke", "#bbb"),
    }
    if radius is not None:
        rect["radius"] = radius
    if "stroke_style" in merged:
        rect["stroke_style"] = merged["stroke_style"]
    children: list[dict[str, Any]] = [rect]
    layout = merged.get("internal_layout") if isinstance(merged.get("internal_layout"), dict) else {}
    for slot, value, fallback in (
        ("title", obj.get("title"), {"box_offset": [0, 6, "100%", 18], "style": "heading"}),
        ("body", obj.get("body"), {"box_offset": [8, 26, "calc(100% - 16)", "calc(100% - 30)"], "style": "body"}),
    ):
        if value in (None, ""):
            continue
        slot_layout = layout.get(slot) if isinstance(layout.get(slot), dict) else {}
        slot_layout = {**fallback, **slot_layout}
        text_obj: dict[str, Any] = {
            "type": "text",
            "box": _slot_box(local_box, slot_layout.get("box_offset")),
            "text": str(value),
        }
        if slot_layout.get("style"):
            text_obj["style"] = slot_layout["style"]
        children.append(text_obj)
    group: dict[str, Any] = {
        "type": "group",
        "box": list(box),
        "children": children,
        "meta": {"source_component": spec_name},
    }
    for key in ("id", "decorative", "z", "opacity", "style"):
        if key in obj:
            group[key] = obj[key]
    return group


#: render() styling keys a `graph` object may pass through verbatim.
_GRAPH_RENDER_KEYS = frozenset({
    "node_radius", "node_fill", "node_stroke", "node_stroke_width",
    "edge_color", "edge_width", "labels", "label_color", "label_size",
    "font_family",
})
#: named layout algorithms a `graph` object may request.
_GRAPH_ALGORITHMS = frozenset({
    "auto", "layered", "spring", "radial", "circular", "grid",
})


def _expand_graph(obj: dict[str, Any]) -> dict[str, Any]:
    """Lower a declarative ``type: graph`` object into a positioned core
    ``group`` (roadmap item 1 — the render-time auto-layout bridge).

    Builds a :class:`~framegraph.sdk.topology.Graph` from the object's
    ``nodes``/``edges``, computes placements with the requested ``algorithm``
    (``auto`` infers from structure), lets any node's explicit ``pos`` OVERRIDE
    its computed position (§A.0), and renders the group fitted to ``box``.
    Styling keys pass through to ``Graph.render``; a bad algorithm degrades to
    a placeholder rather than raising."""
    from framegraph.sdk.topology import Graph

    algorithm = str(obj.get("algorithm") or "auto").strip().lower()
    if algorithm not in _GRAPH_ALGORITHMS:
        return _invalid_placeholder(obj, "unknown-graph-algorithm", algorithm)

    g = Graph()
    overrides: dict[str, Any] = {}
    for node in obj.get("nodes") or []:
        if not isinstance(node, dict):
            continue
        nid = node.get("id")
        if nid is None:
            continue
        extra = {k: v for k, v in node.items()
                 if k not in {"id", "label", "weight", "pos"}}
        g.node(nid, node.get("label"), weight=float(node.get("weight", 1.0)),
               **extra)
        if _is_point(node.get("pos")):
            overrides[str(nid)] = list(node["pos"])
    for edge in obj.get("edges") or []:
        if not isinstance(edge, dict):
            continue
        src = edge.get("from", edge.get("src"))
        dst = edge.get("to", edge.get("dst"))
        if src is None or dst is None:
            continue
        g.edge(str(src), str(dst), directed=bool(edge.get("directed")),
               label=edge.get("label"), weight=float(edge.get("weight", 1.0)))

    positions = _graph_positions(g, algorithm, obj.get("root"))
    positions.update({k: v for k, v in overrides.items() if k in positions})

    box = obj.get("box") if _is_box(obj.get("box")) else [0, 0, 1, 1]
    render_kwargs = {k: obj[k] for k in _GRAPH_RENDER_KEYS if k in obj}
    group = g.render(positions=positions or None, box=list(box),
                     id=obj.get("id"), **render_kwargs)
    if obj.get("decorative"):
        group["decorative"] = True
    return group


def _graph_positions(graph: Any, algorithm: str, root: Any) -> dict[str, Any]:
    """Node positions for the requested algorithm (``auto`` infers)."""
    if not graph.nodes:
        return {}
    if algorithm == "auto":
        return {k: [v.x, v.y] for k, v in graph.auto_layout().items()}
    if algorithm == "radial":
        r = root if isinstance(root, str) and root else graph._auto_root()
        vecs = graph.radial_layout(r) if r else graph.grid_layout()
    else:
        vecs = getattr(graph, f"{algorithm}_layout")()
    return {k: [v.x, v.y] for k, v in vecs.items()}


def _is_point(value: Any) -> bool:
    return (isinstance(value, (list, tuple)) and len(value) >= 2
            and all(isinstance(v, (int, float)) for v in value[:2]))


def _invalid_placeholder(obj: dict[str, Any], reason: str, ref: Any) -> dict[str, Any]:
    box = obj.get("box") if _is_box(obj.get("box")) else [0, 0, 1, 1]
    return {
        "type": "group",
        "id": obj.get("id"),
        "box": list(box),
        "children": [],
        "meta": {"sdk_expand_error": reason, "ref": ref},
    }


def _subst(value: Any, context: dict[str, Any]) -> Any:
    if isinstance(value, str) and value.startswith("$"):
        return copy.deepcopy(context.get(value[1:], value))
    if isinstance(value, list):
        return [_subst(item, context) for item in value]
    if isinstance(value, dict):
        return {key: _subst(item, context) for key, item in value.items()}
    return value


def _map_object(obj: dict[str, Any], source_box: list[Any], target_box: list[Any]) -> dict[str, Any]:
    out = copy.deepcopy(obj)
    sx, sy, sw, sh = [float(v) for v in source_box[:4]]
    tx, ty, tw, th = [float(v) for v in target_box[:4]]
    scale_x = tw / sw if sw else 1.0
    scale_y = th / sh if sh else 1.0

    def point(pt: Any) -> Any:
        if isinstance(pt, list) and len(pt) >= 2 and all(isinstance(v, (int, float)) for v in pt[:2]):
            return [tx + (float(pt[0]) - sx) * scale_x, ty + (float(pt[1]) - sy) * scale_y, *pt[2:]]
        return pt

    if _is_box(out.get("box")):
        bx, by, bw, bh = [float(v) for v in out["box"][:4]]
        out["box"] = [tx + (bx - sx) * scale_x, ty + (by - sy) * scale_y, bw * scale_x, bh * scale_y]
    for key in ("from", "to", "center"):
        if key in out:
            out[key] = point(out[key])
    if isinstance(out.get("points"), list):
        out["points"] = [point(p) for p in out["points"]]
    if isinstance(out.get("ports"), dict):
        out["ports"] = {name: point(p) for name, p in out["ports"].items()}
    if out.get("type") == "path" and isinstance(out.get("d"), str):
        out["d"] = _map_path_d(out["d"], point)
    if isinstance(out.get("children"), list):
        out["children"] = [_map_object(child, source_box, target_box) for child in out["children"] if isinstance(child, dict)]
    return out


def _map_path_d(d: str, point_fn) -> str:
    tokens = re.findall(r"[A-Za-z]|[-+]?(?:\d*\.\d+|\d+)(?:[eE][-+]?\d+)?", d)
    out: list[str] = []
    i = 0
    current = ""
    pair_commands = {"M", "L", "T"}
    curve_commands = {"C"}
    quad_commands = {"Q", "S"}
    while i < len(tokens):
        tok = tokens[i]
        if re.fullmatch(r"[A-Za-z]", tok):
            current = tok
            out.append(tok)
            i += 1
            continue
        cmd = current.upper()
        if cmd in pair_commands and i + 1 < len(tokens):
            p = point_fn([float(tokens[i]), float(tokens[i + 1])])
            out.extend([_fmt(p[0]), _fmt(p[1])])
            i += 2
        elif cmd in quad_commands and i + 3 < len(tokens):
            for _ in range(2):
                p = point_fn([float(tokens[i]), float(tokens[i + 1])])
                out.extend([_fmt(p[0]), _fmt(p[1])])
                i += 2
        elif cmd in curve_commands and i + 5 < len(tokens):
            for _ in range(3):
                p = point_fn([float(tokens[i]), float(tokens[i + 1])])
                out.extend([_fmt(p[0]), _fmt(p[1])])
                i += 2
        else:
            out.append(tok)
            i += 1
    return " ".join(out)


def _slot_box(component_box: list[Any], offset: Any) -> list[float]:
    x, y, w, h = [float(v) for v in component_box[:4]]
    if not isinstance(offset, list) or len(offset) < 4:
        offset = [0, 0, w, h]
    ox = _component_length(offset[0], w)
    oy = _component_length(offset[1], h)
    ow = _component_length(offset[2], w)
    oh = _component_length(offset[3], h)
    return [x + ox, y + oy, ow, oh]


def _component_length(value: Any, total: float) -> float:
    if isinstance(value, (int, float)):
        return float(value)
    if not isinstance(value, str):
        return 0.0
    s = value.strip()
    if s.endswith("%"):
        return total * (float(s[:-1]) / 100.0)
    if s.startswith("calc(") and s.endswith(")"):
        inner = s[5:-1].strip()
        match = re.fullmatch(r"100%\s*-\s*([-+]?\d+(?:\.\d+)?)", inner)
        if match:
            return total - float(match.group(1))
    try:
        return float(s.removesuffix("px"))
    except ValueError:
        return 0.0


def _is_box(value: Any) -> bool:
    return isinstance(value, list) and len(value) >= 4 and all(isinstance(v, (int, float)) for v in value[:4])


def _fmt(value: float) -> str:
    return f"{value:.6g}"


__all__ = ["ExpandOptions", "ExpandedDocument", "expand"]
