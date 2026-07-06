"""Data-driven page generators (issue #32).

Faithful v2 ports of the predecessor project's two symbol-pack build
scripts — same input data contract, same geometry:

- :func:`honeycomb_capability_map` — columns of flat-top hex cells under
  header hexes (the capability-coverage slide);
- :func:`module_hub_radial` — a hub hex with satellite hexes at explicit
  positions, connected by edges drawn beneath the nodes.

Both consume a plain data dict (see ``data/examples/*.yml`` for committed
samples, loadable via :func:`load_example`), author a document that
instantiates the ``hex`` symbol pack through grammar-level ``use`` objects,
then lower it through :func:`framegraph.sdk.expand` — the returned document
is plain core primitives, validated and render-ready.

v0.1 → v2 notes: per-node colors were injected as ``hash()``-derived color
tokens (nondeterministic across interpreters); v2 fill/stroke accept hex
literals, so node colors pass straight through and the output is
deterministic. Per-node label colors become inline text styles.
"""
from __future__ import annotations

import copy
import math
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

from framegraph.library.symbols import load_symbols, support_text_styles
from framegraph.sdk.expand import expand
from framegraph.sdk.model import HEAD_VERSION

EXAMPLES_DIR = Path(__file__).resolve().parent / "data" / "examples"

_FONT = ["Arial", "Helvetica", "sans-serif"]

HONEYCOMB_PALETTE: dict[str, str] = {
    "bg": "#FFFFFF",
    "title_color": "#1A2B3E",
    "kicker_color": "#9A9A9A",
    "dot_primary": "#E51A4C",
    "dot_secondary": "#1A2B3E",
    "dot_tertiary": "#C8C8C8",
    "header_fill": "#1A56B0",
    "leaf_fill": "#FFFFFF",
    "outline_core": "#1A56B0",
    "outline_extended": "#7FBA3A",
    "outline_future": "#7FBA3A",
    "header_text_color": "#FFFFFF",
    "leaf_text_color": "#1A2B3E",
    "page_number_color": "#9A9A9A",
}

HONEYCOMB_GEOMETRY: dict[str, float] = {
    "canvas_w": 1280, "canvas_h": 1000,
    "hex_w": 150, "hex_h": 130,
    "column_pitch_x": 130, "row_pitch_y": 135, "column_offset_y": 68,
    "left_margin": 60, "top_margin": 140,
}

MODULE_PALETTE: dict[str, str] = {
    "bg": "#FFFFFF",
    "title_color": "#1A2B3E",
    "kicker_color": "#9A9A9A",
    "dot_primary": "#E51A4C",
    "dot_secondary": "#1A2B3E",
    "dot_tertiary": "#C8C8C8",
    "edge_color": "#C8C8C8",
    "page_number_color": "#9A9A9A",
}

MODULE_GEOMETRY: dict[str, float] = {
    "canvas_w": 1280, "canvas_h": 900,
    "satellite_default_size": 70, "label_gap": 6,
}

_ICON_TO_SYMBOL = {
    "warning": "hex_node_warning",
    "excel": "hex_node_excel",
    "money": "hex_node_money",
    "none": "hex_node_plain",
}


@lru_cache(maxsize=None)
def _load_example_raw(name: str) -> dict[str, Any]:
    path = EXAMPLES_DIR / f"{name}.yml"
    if not path.is_file():
        raise KeyError(f"unknown example {name!r}; available: "
                       f"{sorted(p.stem for p in EXAMPLES_DIR.glob('*.yml'))}")
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def load_example(name: str) -> dict[str, Any]:
    """One committed generator input (``honeycomb`` / ``module_hub``)."""
    return copy.deepcopy(_load_example_raw(name))


def _text_style(size: float, weight: int, color: str, align: str,
                valign: str = "middle", line_height: float | None = None,
                ) -> dict[str, Any]:
    style: dict[str, Any] = {
        "font_family": _FONT, "font_size": size, "font_weight": weight,
        "color": color, "align": align, "vertical_align": valign}
    if line_height is not None:
        style["line_height"] = line_height
    return style


def _chrome(objects: list[dict[str, Any]], data: dict[str, Any],
            geo: dict[str, float], prefix: str) -> None:
    """Decorator dots, title, optional kicker — shared page furniture."""
    for name, y in (("dot_primary", 14), ("dot_secondary", 44),
                    ("dot_tertiary", 92)):
        objects.append({"type": "ellipse", "id": name, "center": [31, y + 9],
                        "rx": 9, "ry": 9, "fill": name})
    objects.append({"type": "text", "id": "title",
                    "box": [60, 12, geo["canvas_w"] - 80, 56],
                    "text": data["title"], "style": f"{prefix}_title"})
    kicker = (data.get("kicker_label") or "").strip()
    if kicker:
        objects.append({"type": "text", "id": "kicker",
                        "box": [60, 88, geo["canvas_w"] - 80, 24],
                        "text": kicker, "style": f"{prefix}_kicker"})


def _page_number(objects: list[dict[str, Any]], data: dict[str, Any],
                 geo: dict[str, float], prefix: str) -> None:
    page_num = data.get("page_number")
    if page_num not in (None, ""):
        objects.append({"type": "text", "id": "page_number",
                        "box": [0, geo["canvas_h"] - 28, geo["canvas_w"], 18],
                        "text": str(page_num),
                        "style": f"{prefix}_page_number"})


def _finish(data: dict[str, Any], objects: list[dict[str, Any]],
            colors: dict[str, str], text_styles: dict[str, Any],
            geo: dict[str, float], page_id: str) -> dict[str, Any]:
    """Wrap objects in an authored doc, lower ``use``, return the plain doc."""
    authored = {
        "dsl": "FrameGraph", "version": HEAD_VERSION,
        "title": data["title"], "profile": "deck",
        "defs": {"tokens": {"colors": colors, "text_styles": text_styles},
                 "symbols": load_symbols("hex")},
        "pages": [{"mode": "page", "id": page_id,
                   "canvas": {"size": [geo["canvas_w"], geo["canvas_h"]],
                              "units": "px"},
                   "rendering": {"coordinate_mode": "absolute"},
                   "layers": [{"id": "main", "objects": objects}]}],
    }
    expanded = expand(authored).document
    plain = expanded.model_dump(by_alias=True, exclude_none=True)
    # `use` is fully lowered: the symbol bodies are dead weight (and out of
    # the HEAD core profile) in the returned document.
    plain["defs"].pop("symbols", None)
    return plain


# ── Honeycomb capability map ────────────────────────────────────────────


def honeycomb_capability_map(data: dict[str, Any]) -> dict[str, Any]:
    """Columns of hex capability cells (required: ``title``, ``columns``).

    Each column: ``header`` plus ``items`` of ``{label, variant}`` where
    variant ∈ core / extended / future (future = dashed outline). Odd
    columns drop by ``column_offset_y`` unless the column pins ``offset``.
    """
    pal = {**HONEYCOMB_PALETTE, **(data.get("palette") or {})}
    geo = {**HONEYCOMB_GEOMETRY, **(data.get("geometry") or {})}
    hex_w, hex_h = geo["hex_w"], geo["hex_h"]

    objects: list[dict[str, Any]] = []
    _chrome(objects, data, geo, "honeycomb")
    deepest = 0.0

    for col_idx, col in enumerate(data["columns"]):
        declared = col.get("offset") or "auto"
        offset = ("shifted" if col_idx % 2 == 1 else "top") \
            if declared == "auto" else declared
        col_x = geo["left_margin"] + col_idx * geo["column_pitch_x"]
        col_top_y = geo["top_margin"] + (geo["column_offset_y"]
                                         if offset == "shifted" else 0)
        objects.append({"type": "use", "id": f"col{col_idx}_header",
                        "symbol": "hex_header",
                        "box": [col_x, col_top_y, hex_w, hex_h],
                        "params": {"header_fill": "header_fill",
                                   "label": col["header"]}})
        for item_idx, item in enumerate(col["items"]):
            cell_y = col_top_y + (item_idx + 1) * geo["row_pitch_y"]
            variant = (item.get("variant") or "core").lower()
            outline = {"core": "outline_core", "extended": "outline_extended",
                       "future": "outline_future"}.get(variant, "outline_core")
            symbol = "hex_leaf_dashed" if variant == "future" else "hex_leaf_solid"
            objects.append({"type": "use", "id": f"col{col_idx}_item{item_idx}",
                            "symbol": symbol,
                            "box": [col_x, cell_y, hex_w, hex_h],
                            "params": {"leaf_fill": "leaf_fill",
                                       "outline_color": outline,
                                       "label": item["label"]}})
            deepest = max(deepest, cell_y + hex_h)

    # v0.1 pinned canvas_h and let a shifted six-row column clip at the
    # bottom edge; grow to fit unless the data pins the height itself.
    if "canvas_h" not in (data.get("geometry") or {}):
        geo["canvas_h"] = max(geo["canvas_h"], deepest + 40)
    _page_number(objects, data, geo, "honeycomb")

    text_styles = {
        **support_text_styles("hex"),
        "honeycomb_title": _text_style(32, 400, "title_color", "left", "top", 38),
        "honeycomb_kicker": _text_style(18, 400, "kicker_color", "left"),
        "honeycomb_page_number": _text_style(13, 400, "page_number_color",
                                             "center"),
    }
    return _finish(data, objects, pal, text_styles, geo, "honeycomb-map")


# ── Radial module hub ───────────────────────────────────────────────────


def _hex_box(cx: float, cy: float, side: float) -> list[float]:
    """[x, y, w, h] of a flat-top hex centered at (cx, cy)."""
    w = 2.0 * side
    h = math.sqrt(3.0) * side
    return [cx - w / 2.0, cy - h / 2.0, w, h]


def _label_box(hex_box: list[float], anchor: str,
               gap: float) -> tuple[list[float], str]:
    """([x, y, w, h], align) for a two-line label outside a hex."""
    x, y, w, h = hex_box
    if anchor == "below":
        return [x - 40, y + h + gap, w + 80, 44], "center"
    if anchor == "left":
        return [x - 230, y + h / 2.0 - 22, 220, 44], "right"
    if anchor == "right":
        return [x + w + gap, y + h / 2.0 - 22, 220, 44], "left"
    return [x - 40, y - 44 - gap, w + 80, 44], "center"


def module_hub_radial(data: dict[str, Any]) -> dict[str, Any]:
    """Hub-and-satellites module map (required: ``title``, ``hub``,
    ``satellites``); every node carries an explicit ``position`` and
    optional ``size`` / ``icon`` / ``outline_color`` / ``label_color`` /
    ``label_anchor``; ``edges`` connect node ids beneath the hexes."""
    pal = {**MODULE_PALETTE, **(data.get("palette") or {})}
    geo = {**MODULE_GEOMETRY, **(data.get("geometry") or {})}
    sat_default = geo["satellite_default_size"]

    objects: list[dict[str, Any]] = []
    _chrome(objects, data, geo, "module")

    hub = data["hub"]
    hub_cx, hub_cy = (float(v) for v in hub["position"])
    hub_size = float(hub.get("size") or 130)
    registry: dict[str, tuple[float, float]] = {hub["id"]: (hub_cx, hub_cy)}
    for sat in data["satellites"]:
        registry[sat["id"]] = (float(sat["position"][0]),
                               float(sat["position"][1]))

    # Edges first, so the hexes paint over them.
    for edge_idx, edge in enumerate(data.get("edges") or []):
        src, tgt = registry.get(edge["from"]), registry.get(edge["to"])
        if not src or not tgt:
            continue
        stroke_style: dict[str, Any] = {
            "stroke_width": float(edge.get("stroke_width") or 1.5)}
        if edge.get("dash"):
            stroke_style["stroke_dasharray"] = list(edge["dash"])
        objects.append({"type": "line", "id": f"edge_{edge_idx}",
                        "from": list(src), "to": list(tgt),
                        "stroke": edge.get("stroke_color") or "edge_color",
                        "stroke_style": stroke_style})

    hub_box = _hex_box(hub_cx, hub_cy, hub_size)
    objects.append({"type": "text", "id": "hub_label",
                    "box": [hub_box[0] - 40, hub_box[1] - 90,
                            hub_box[2] + 80, 80],
                    "text": hub["label"],
                    "style": _text_style(30, 400,
                                         hub.get("label_color") or "#E58938",
                                         "center", "middle", 36)})
    hub_icon = (hub.get("icon") or "warning").lower()
    objects.append({"type": "use", "id": f"node_{hub['id']}",
                    "symbol": _ICON_TO_SYMBOL.get(hub_icon, "hex_node_warning"),
                    "box": hub_box,
                    "params": {"outline_color": hub.get("outline_color")
                               or "#9E1A8C",
                               "fill": hub.get("fill") or "bg"}})

    for sat in data["satellites"]:
        sat_size = float(sat.get("size") or sat_default)
        sat_cx, sat_cy = registry[sat["id"]]
        sat_box = _hex_box(sat_cx, sat_cy, sat_size)
        icon = (sat.get("icon") or "warning").lower()
        objects.append({"type": "use", "id": f"node_{sat['id']}",
                        "symbol": _ICON_TO_SYMBOL.get(icon, "hex_node_warning"),
                        "box": sat_box,
                        "params": {"outline_color": sat.get("outline_color")
                                   or "#1A56B0",
                                   "fill": sat.get("fill") or "bg"}})
        lab_box, lab_align = _label_box(
            sat_box, sat.get("label_anchor") or "above", geo["label_gap"])
        objects.append({"type": "text", "id": f"label_{sat['id']}",
                        "box": lab_box, "text": sat["label"],
                        "style": _text_style(
                            14, 400, sat.get("label_color") or "#1A2B3E",
                            lab_align, "middle", 18)})

    # Hub detail block last: it is a foreground annotation, painted above
    # the node layer (v0.1 drew it before the satellites, which let nearby
    # hexes clip the heading — the committed example exercises exactly that).
    detail = hub.get("detail") or {}
    if detail:
        d_box = list(detail["box"]) if detail.get("box") else \
            [hub_box[0] - 60, hub_box[1] + hub_box[3] + 12,
             hub_box[2] + 120, 160]
        objects.append({"type": "text", "id": "hub_detail_heading",
                        "box": [d_box[0], d_box[1], d_box[2], 24],
                        "text": detail.get("heading") or "",
                        "style": _text_style(
                            16, 700,
                            detail.get("heading_color")
                            or hub.get("outline_color") or "#9E1A8C",
                            "left", "top")})
        bullets = detail.get("bullets") or []
        if bullets:
            objects.append({"type": "bullet_list", "id": "hub_detail_bullets",
                            "box": [d_box[0] + 24, d_box[1] + 32,
                                    d_box[2] - 24, d_box[3] - 32],
                            "items": list(bullets),
                            "style": _text_style(13, 400, "#1A2B3E",
                                                 "left", "top", 18)})
    _page_number(objects, data, geo, "module")

    text_styles = {
        **support_text_styles("hex"),
        "module_title": _text_style(32, 400, "title_color", "left", "top", 38),
        "module_kicker": _text_style(18, 400, "kicker_color", "left"),
        "module_page_number": _text_style(13, 400, "page_number_color",
                                          "center"),
    }
    return _finish(data, objects, pal, text_styles, geo, "module-hub")


__all__ = ["EXAMPLES_DIR", "HONEYCOMB_GEOMETRY", "HONEYCOMB_PALETTE",
           "MODULE_GEOMETRY", "MODULE_PALETTE", "honeycomb_capability_map",
           "load_example", "module_hub_radial"]
