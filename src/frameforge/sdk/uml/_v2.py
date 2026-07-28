"""Boundary adapter from absorbed UML composer output to FrameForge v2.

The sibling composers were intentionally kept algorithmically intact.  This
module owns the one version-sensitive concern: converting their legacy visual
dictionary spelling into model-valid v2 page objects.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any

from frameforge.model import HEAD_VERSION


_STROKE_KEYS = {
    "width": "stroke_width",
    "dash": "stroke_dasharray",
    "linecap": "stroke_linecap",
    "linejoin": "stroke_linejoin",
    "arrow_start": "arrow_start",
    "arrow_end": "arrow_end",
}

_PORTABLE_UML_TYPES = {
    "uml.fragment_frame",
    "uml.swimlane",
    "uml.timing_lane",
}


def _normalize_style(style: Any) -> Any:
    if not isinstance(style, dict):
        return style
    result = dict(style)
    if "size" in result and "font_size" not in result:
        result["font_size"] = result.pop("size")
    if "align" in result and "text_align" not in result:
        result["text_align"] = result.pop("align")
    if "wrap" in result and "white_space" not in result:
        result["white_space"] = "normal" if result.pop("wrap") else "nowrap"
    else:
        result.pop("wrap", None)
    return result


def _normalize_stroke(obj: dict[str, Any]) -> None:
    stroke = obj.get("stroke")
    if not isinstance(stroke, dict):
        return
    paint = stroke.get("color", "#1A1A1A")
    geometry: dict[str, Any] = {}
    for legacy, current in _STROKE_KEYS.items():
        if legacy in stroke:
            geometry[current] = stroke[legacy]
    for end in ("start", "end"):
        kind = stroke.get(f"arrow_{end}_kind")
        enabled = stroke.get(f"arrow_{end}")
        if kind is not None:
            geometry[f"arrow_{end}"] = kind
        elif enabled is not None:
            geometry[f"arrow_{end}"] = enabled
    obj["stroke"] = paint
    if geometry:
        existing = obj.get("stroke_style")
        if isinstance(existing, dict):
            geometry = {**existing, **geometry}
        obj["stroke_style"] = geometry


def _portable_text(
    object_id: str,
    box: list[float],
    text: str,
    *,
    bold: bool = False,
) -> dict[str, Any]:
    return {
        "type": "text",
        "id": object_id,
        "box": box,
        "text": text,
        "decorative": True,
        "style": {
            "color": "#1A1A1A",
            "font_size": 10,
            "font_weight": 700 if bold else 400,
            "white_space": "normal",
        },
    }


def _portable_line(object_id: str, start: list[float], end: list[float]) -> dict[str, Any]:
    return {
        "type": "line",
        "id": object_id,
        "from": start,
        "to": end,
        "decorative": True,
        "stroke": "#777777",
        "stroke_style": {"stroke_width": 0.75},
    }


def _lower_portable_uml(obj: dict[str, Any]) -> dict[str, Any]:
    """Lower UML forms without canonical SVG dispatch into core v2 primitives."""
    uml_type = obj.get("type")
    box = obj.get("box")
    if uml_type not in _PORTABLE_UML_TYPES or not isinstance(box, list) or len(box) < 4:
        return obj

    _x, _y, width, height = (float(value) for value in box[:4])
    base_id = str(obj.get("id") or uml_type.removeprefix("uml."))
    children: list[dict[str, Any]] = [
        {
            "type": "rect",
            "id": f"{base_id}.frame",
            "box": [0.0, 0.0, width, height],
            "decorative": True,
            "fill": "none",
            "stroke": "#555555",
            "stroke_style": {"stroke_width": 1.0},
        }
    ]

    if uml_type == "uml.fragment_frame":
        kind = str(obj.get("kind") or "fragment")
        children.append(_portable_text(f"{base_id}.kind", [4.0, 2.0, 72.0, 16.0], kind, bold=True))
        operands = obj.get("operands") if isinstance(obj.get("operands"), list) else []
        for index, operand in enumerate(operands):
            children.append(
                _portable_text(
                    f"{base_id}.operand.{index}",
                    [8.0, 22.0 + index * 18.0, max(width - 16.0, 1.0), 16.0],
                    str(operand),
                )
            )
        for index, divider in enumerate(obj.get("dividers") or []):
            local_y = float(divider) - float(box[1])
            children.append(_portable_line(f"{base_id}.divider.{index}", [0.0, local_y], [width, local_y]))
    elif uml_type == "uml.swimlane":
        children.append(
            _portable_text(
                f"{base_id}.name",
                [6.0, 4.0, max(width - 12.0, 1.0), 18.0],
                str(obj.get("name") or "swimlane"),
                bold=True,
            )
        )
        children.append(_portable_line(f"{base_id}.header", [0.0, 26.0], [width, 26.0]))
    else:
        label_width = min(float(obj.get("label_width") or 96.0), width)
        states = obj.get("states") if isinstance(obj.get("states"), list) else []
        children.append(
            _portable_text(
                f"{base_id}.name",
                [4.0, 2.0, max(label_width - 8.0, 1.0), 16.0],
                str(obj.get("name") or "timing"),
                bold=True,
            )
        )
        children.append(_portable_line(f"{base_id}.label-divider", [label_width, 0.0], [label_width, height]))
        row_height = height / max(len(states), 1)
        for index, state in enumerate(states):
            row_y = index * row_height
            children.append(
                _portable_text(
                    f"{base_id}.state.{index}",
                    [4.0, row_y + 18.0, max(label_width - 8.0, 1.0), max(row_height - 20.0, 1.0)],
                    str(state),
                )
            )
            if index:
                children.append(_portable_line(f"{base_id}.row.{index}", [0.0, row_y], [width, row_y]))

    lowered: dict[str, Any] = {
        "type": "group",
        "id": obj.get("id"),
        "box": list(box[:4]),
        "children": children,
        "meta": {"uml_type": uml_type},
    }
    for key in ("z", "opacity", "rotation", "decorative", "containment", "overlap"):
        if key in obj:
            lowered[key] = obj[key]
    return lowered


def _normalize_object(value: dict[str, Any]) -> dict[str, Any]:
    obj = _lower_portable_uml(deepcopy(value))
    _normalize_stroke(obj)
    if "style" in obj:
        obj["style"] = _normalize_style(obj["style"])
    if obj.get("type") == "connector":
        for endpoint in ("from", "to"):
            if isinstance(obj.get(endpoint), str):
                obj[endpoint] = {"ref": obj[endpoint]}
    if obj.get("type") == "ellipse" and isinstance(obj.get("box"), list):
        x, y, width, height = obj["box"][:4]
        obj.setdefault("center", [x + width / 2, y + height / 2])
        obj.setdefault("rx", width / 2)
        obj.setdefault("ry", height / 2)
    legacy_group_children = (
        obj.get("type") == "group" and "children" not in obj and "objects" in obj
    )
    if legacy_group_children:
        obj["children"] = obj.pop("objects")
    for key in ("children", "objects"):
        if isinstance(obj.get(key), list):
            obj[key] = [
                _normalize_object(child) if isinstance(child, dict) else child
                for child in obj[key]
            ]
    if legacy_group_children and isinstance(obj.get("box"), list):
        origin_x, origin_y = obj["box"][:2]
        for child in obj.get("children", []):
            child_box = child.get("box") if isinstance(child, dict) else None
            if isinstance(child_box, list) and len(child_box) >= 2:
                child["box"] = [
                    child_box[0] - origin_x,
                    child_box[1] - origin_y,
                    *child_box[2:],
                ]
    return obj


def normalize_visual(visual: dict[str, Any]) -> dict[str, Any]:
    """Return a deep-copied visual block containing only v2 object spellings."""
    result = deepcopy(visual)
    for layer in result.get("layers", []):
        layer["objects"] = [
            _normalize_object(obj) if isinstance(obj, dict) else obj
            for obj in layer.get("objects", [])
        ]
    return result


def visual_to_page(
    visual: dict[str, Any],
    *,
    page_id: str = "uml",
    canvas_size: tuple[float, float] = (1280.0, 720.0),
) -> dict[str, Any]:
    """Wrap a composed visual block as a FrameForge v2 absolute page."""
    return {
        "mode": "page",
        "id": page_id,
        "canvas": {"size": [float(canvas_size[0]), float(canvas_size[1])], "units": "px"},
        "rendering": {"coordinate_mode": "absolute"},
        "layers": deepcopy(visual.get("layers", [])),
    }


def visual_to_document(
    visual: dict[str, Any],
    *,
    title: str = "UML diagram",
    page_id: str = "uml",
    canvas_size: tuple[float, float] = (1280.0, 720.0),
) -> dict[str, Any]:
    """Wrap a composed visual block as a complete FrameForge v2 document."""
    document: dict[str, Any] = {
        "dsl": "FrameForge",
        "version": HEAD_VERSION,
        "profile": "diagram",
        "title": title,
        "pages": [visual_to_page(visual, page_id=page_id, canvas_size=canvas_size)],
    }
    tokens = visual.get("tokens")
    if tokens:
        document["defs"] = {"tokens": deepcopy(tokens)}
    return document


__all__ = ["normalize_visual", "visual_to_document", "visual_to_page"]
