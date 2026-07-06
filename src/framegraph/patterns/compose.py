"""Compose a filled pattern into a v2 page (issue #29 — the render bridge).

``compose(pattern_id, fill)`` validates the payload through the #28 fill
contract, computes zone boxes **deterministically** from the pattern's
placement vocabulary, applies the ``enterprise_layout`` treatments (card
fill/stroke/corner, accent bar, label slot), and emits plain core objects —
``rect`` / ``text`` / ``bullet_list`` / ``table`` / ``image`` — on one
absolute 1920×1080 page. Nothing new enters the schema; the returned
document has already passed :func:`~framegraph.sdk.model.validate_document`.

Layout families (all 17 sidecared patterns fall in the first three; the
rules are general):

- every zone anchored ``v: middle`` → one column band per zone, ordered
  left → center → right, then declaration order;
- unique ``(h, v)`` anchors on a top/bottom grid → a row×column grid
  (the SWOT/RAID quadrant family);
- mixed anchors (the Business Model Canvas family) → columns grouped by
  ``h``, zones stacked by ``v`` within a column, widths weighted by the
  zone size vocabulary;
- zones without anchors stack in declaration order (regions/relative are
  approximated — the catalog's sidecared set never needs them).

Colour and font tokens used by the treatments (``surface``, ``border``,
``accent`` …) are emitted into ``defs.tokens`` from :data:`DEFAULT_TOKENS`;
override wholesale via ``tokens=``.
"""
from __future__ import annotations

from typing import Any

from framegraph.patterns.catalog import PatternZone, SlidePattern, load_catalog
from framegraph.patterns.fill import load_fill
from framegraph.sdk.model import HEAD_VERSION, validate_document

CANVAS_W, CANVAS_H = 1920.0, 1080.0
MARGIN, HEADER_H, GAP = 64.0, 108.0, 24.0

DEFAULT_TOKENS: dict[str, str] = {
    "surface": "#f7f5f0",
    "border": "#d9d3c7",
    "text": "#1d1e22",
    "text_muted": "#6c7077",
    "primary": "#233042",
    "accent": "#0f7d88",
    "accent_warm": "#b5642c",
    "data_3": "#3f7d4e",
    "paper": "#fcfbf8",
}
_FONTS = {"primary": ["Inter", "DejaVu Sans", "sans-serif"],
          "heading": ["Inter", "DejaVu Sans", "sans-serif"]}
_SIZE_WEIGHT = {"xs": 1.0, "small": 2.0, "medium": 3.0, "equal": 3.0,
                "variable": 3.0, "contextual": 3.0, "large": 4.5,
                "xl": 5.0, "full": 5.0}
_H_ORDER = {"left": 0, "center": 1, "right": 2}
_V_ORDER = {"top": 0, "middle": 1, "bottom": 2}


def _zone_boxes(pattern: SlidePattern) -> dict[str, list[float]]:
    """Deterministic zone geometry inside the content rectangle."""
    x0, y0 = MARGIN, MARGIN + HEADER_H
    width, height = CANVAS_W - 2 * MARGIN, CANVAS_H - MARGIN - y0
    zones = pattern.zones
    anchors = [z.placement.anchor if (z.placement and z.placement.anchor) else None
               for z in zones]

    def band_layout(ordered: list[PatternZone]) -> dict[str, list[float]]:
        weights = [_SIZE_WEIGHT.get(z.size, 3.0) for z in ordered]
        total = sum(weights)
        boxes, x = {}, x0
        for z, w in zip(ordered, weights):
            zw = (width - GAP * (len(ordered) - 1)) * w / total
            boxes[z.role] = [x, y0, zw, height]
            x += zw + GAP
        return boxes

    if all(a is not None and a.v == "middle" for a in anchors):
        order = sorted(range(len(zones)),
                       key=lambda i: (_H_ORDER[anchors[i].h], i))
        return band_layout([zones[i] for i in order])

    if all(a is not None for a in anchors):
        cells = {(a.h, a.v) for a in anchors}
        if len(cells) == len(zones):        # unique cells → a clean grid
            hs = sorted({a.h for a in anchors}, key=_H_ORDER.get)
            vs = sorted({a.v for a in anchors}, key=_V_ORDER.get)
            cw = (width - GAP * (len(hs) - 1)) / len(hs)
            ch = (height - GAP * (len(vs) - 1)) / len(vs)
            return {z.role: [x0 + hs.index(a.h) * (cw + GAP),
                             y0 + vs.index(a.v) * (ch + GAP), cw, ch]
                    for z, a in zip(zones, anchors)}
        # mixed (the BMC family): columns by h, stacked by v within a column
        columns: dict[str, list[int]] = {}
        for i, a in enumerate(anchors):
            columns.setdefault(a.h, []).append(i)
        hs = sorted(columns, key=_H_ORDER.get)
        col_w = {h: max(_SIZE_WEIGHT.get(zones[i].size, 3.0) for i in columns[h])
                 for h in hs}
        total_w = sum(col_w.values())
        boxes, x = {}, x0
        for h in hs:
            zw = (width - GAP * (len(hs) - 1)) * col_w[h] / total_w
            members = sorted(columns[h], key=lambda i: (_V_ORDER[anchors[i].v], i))
            zh = (height - GAP * (len(members) - 1)) / len(members)
            for row, i in enumerate(members):
                boxes[zones[i].role] = [x, y0 + row * (zh + GAP), zw, zh]
            x += zw + GAP
        return boxes

    # no/partial anchors: stack in declaration order (documented approximation)
    zh = (height - GAP * (len(zones) - 1)) / len(zones)
    return {z.role: [x0, y0 + i * (zh + GAP), width, zh]
            for i, z in enumerate(zones)}


def _content_lines(content: Any) -> list[str]:
    """Flatten one zone's validated content into display lines."""
    if content is None:
        return []
    if isinstance(content, str):
        return [content]
    if isinstance(content, list):
        out = []
        for item in content:
            if isinstance(item, dict):
                out.append(" — ".join(str(v) for v in item.values() if v is not None))
            else:
                out.append(str(item))
        return out
    if isinstance(content, dict):
        known = {k: content[k] for k in ("title", "body", "label", "value", "trend",
                                         "left", "right", "src", "alt", "units")
                 if content.get(k) is not None}
        if known:
            return [str(v) for v in known.values()]
        return [f"{k}: {v}" for k, v in content.items()]
    return [str(content)]


def _emit_zone(objects: list[dict[str, Any]], zone: PatternZone,
               box: list[float], treatment: dict[str, Any],
               content: Any) -> None:
    x, y, w, h = box
    tr = treatment or {}
    pad = tr.get("padding") or [20, 24, 20, 24]
    card: dict[str, Any] = {"type": "rect", "box": [x, y, w, h],
                            "fill": tr.get("fill_color") or "surface",
                            "stroke": tr.get("stroke_color") or "border"}
    if tr.get("stroke_width"):
        card["stroke_style"] = {"width": float(tr["stroke_width"])}
    if tr.get("corner_radius"):
        card["radius"] = float(tr["corner_radius"])
    objects.append(card)

    bar = tr.get("accent_bar") or {}
    if bar:
        bw = float(bar.get("width", 4))
        bx = x if bar.get("side", "left") == "left" else x + w - bw
        objects.append({"type": "rect", "box": [bx, y, bw, h],
                        "fill": bar.get("color") or "accent"})

    cx, cy = x + float(pad[1]), y + float(pad[0])
    cw = w - float(pad[1]) - float(pad[3])

    label_slot = (tr.get("slots") or {}).get("label") or {}
    ltyp = label_slot.get("typography") or {}
    lh = float(label_slot.get("height", 16))
    objects.append({
        "type": "text", "box": [cx, cy, cw, lh],
        "text": zone.role.replace("_", " ").upper(),
        "style": {"color": ltyp.get("color") or "text_muted",
                  "font_family": _FONTS.get(ltyp.get("font") or "primary"),
                  "font_size": float(ltyp.get("size", 14)),
                  "font_weight": int(ltyp.get("weight", 700)),
                  # single-line label in a slot-height box: without an
                  # explicit unit line-height the ~1.35 default overflows a
                  # 16px slot by ~3px and every zone label counts clipped
                  "line_height": 1.0,
                  "letter_spacing": 0.8}})
    cy += lh + float(label_slot.get("gap_below", 10))

    lines = _content_lines(content)
    if not lines:
        return
    body_h = max(20.0, y + h - float(pad[2]) - cy)
    if zone.content_type == "table_data" and isinstance(content, dict):
        objects.append({"type": "table", "box": [cx, cy, cw, body_h],
                        "columns": [str(c) for c in content["headers"]],
                        "rows": [[str(c) for c in row] for row in content["rows"]]})
        return
    if zone.content_type == "image" and isinstance(content, dict):
        objects.append({"type": "image", "box": [cx, cy, cw, body_h],
                        "src": content["src"], "alt": content.get("alt")})
        return
    if zone.content_type == "metric" and isinstance(content, dict):
        objects.append({"type": "text", "box": [cx, cy, cw, 44],
                        "text": str(content["value"]),
                        "style": {"color": "text", "font_family": _FONTS["heading"],
                                  "font_size": 36, "font_weight": 700}})
        tail = str(content["label"]) + (f" · {content['trend']}" if content.get("trend") else "")
        objects.append({"type": "text", "box": [cx, cy + 50, cw, 20],
                        "text": tail,
                        "style": {"color": "text_muted", "font_family": _FONTS["primary"],
                                  "font_size": 14}})
        return
    objects.append({"type": "bullet_list", "box": [cx, cy, cw, body_h],
                    "items": lines, "marker_color": "accent", "gap": 8,
                    "style": {"color": "text", "font_family": _FONTS["primary"],
                              "font_size": 15, "line_height": 1.35}})


def compose(pattern_id: int, fill: dict[str, Any], *,
            title: str | None = None,
            tokens: dict[str, str] | None = None) -> dict[str, Any]:
    """A filled pattern as a full, validated FrameGraph document.

    Raises ``KeyError`` for an unknown pattern id and
    ``pydantic.ValidationError`` for a payload that fails the fill contract —
    layout never runs on unvalidated content.
    """
    catalog = load_catalog()
    pattern = catalog.get(pattern_id)
    payload = load_fill(pattern_id, fill, catalog=catalog)
    boxes = _zone_boxes(pattern)
    el_zones = (pattern.enterprise_layout.zones
                if pattern.enterprise_layout else None) or {}

    objects: list[dict[str, Any]] = [
        {"type": "rect", "box": [0, 0, CANVAS_W, CANVAS_H], "fill": "paper"},
        {"type": "text", "box": [MARGIN, MARGIN - 8, CANVAS_W - 2 * MARGIN, 20],
         "text": f"PATTERN {pattern.id:03d} · {(pattern.category or 'generic').upper()}",
         "style": {"color": "accent", "font_family": _FONTS["primary"],
                   "font_size": 14, "font_weight": 600, "letter_spacing": 1.2}},
        {"type": "text", "box": [MARGIN, MARGIN + 22, CANVAS_W - 2 * MARGIN, 48],
         "text": title or pattern.name,
         "style": {"color": "text", "font_family": _FONTS["heading"],
                   # single display line in a 48px band: the ~1.35 default
                   # line-height overshoots the box and counts clipped
                   "font_size": 40, "font_weight": 700, "line_height": 1.0}},
    ]
    for zone in pattern.zones:
        _emit_zone(objects, zone, boxes[zone.role],
                   (el_zones.get(zone.role) or {}).get("treatment") or {},
                   payload.get(zone.role))

    doc = {
        "dsl": "FrameGraph", "version": HEAD_VERSION,
        "title": title or pattern.name, "profile": "deck",
        "defs": {"tokens": {"colors": dict(tokens or DEFAULT_TOKENS)}},
        "pages": [{"mode": "page", "id": f"pattern-{pattern.id}",
                   "canvas": {"size": [CANVAS_W, CANVAS_H], "units": "px"},
                   "rendering": {"coordinate_mode": "absolute"},
                   "layers": [{"id": "main", "objects": objects}]}],
    }
    validate_document(doc)
    return doc


__all__ = ["CANVAS_H", "CANVAS_W", "DEFAULT_TOKENS", "compose"]
