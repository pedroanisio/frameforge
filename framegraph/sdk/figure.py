"""Live FrameGraph figure import helpers."""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Literal, Sequence

from framegraph.sdk.geometry import Mat3
from framegraph.sdk.io import parse
from framegraph.sdk.model import HEAD_VERSION, to_plain_dict

FitMode = Literal["contain", "cover", "scale-down", "native", "stretch"]
BoxLike = Sequence[float | int]


@dataclass(frozen=True)
class FigureContent:
    """Resolved live FrameGraph objects from one source page."""

    page_id: str | None
    source_box: tuple[float, float, float, float]
    layers: tuple[str, ...]
    objects: tuple[dict[str, Any], ...]
    defs: dict[str, Any]


@dataclass(frozen=True)
class FigurePlacement:
    """A placed figure group plus the geometry used to place it."""

    group: dict[str, Any]
    source_box: tuple[float, float, float, float]
    target_box: tuple[float, float, float, float]
    drawn_box: tuple[float, float, float, float]
    transform: Mat3
    defs: dict[str, Any]


class FigureRef:
    """Reference a FrameGraph figure source for live import.

    A figure source may be a callable that authors into a ``DocumentBuilder``, an
    existing builder/document/dict, or a ``.fg.yaml``/``.fg.json`` path. Placement
    imports the selected page's objects as normal FrameGraph children, preserving
    editability and validation instead of freezing the figure to an image.
    """

    def __init__(
        self,
        source: Any,
        *,
        page: str | int | None = None,
        validate: bool = True,
        expand_reuse: bool = True,
    ) -> None:
        self.source = source
        self.page = page
        self.validate = validate
        self.expand_reuse = expand_reuse

    @classmethod
    def from_callable(
        cls,
        draw: Callable[[Any], Any],
        *,
        page: str | int | None = None,
        expand_reuse: bool = True,
    ) -> "FigureRef":
        """Create a figure reference from a function that draws into a builder."""
        return cls(draw, page=page, expand_reuse=expand_reuse)

    @classmethod
    def from_document(cls, document: Any, *, page: str | int | None = None) -> "FigureRef":
        """Create a figure reference from a FrameGraph document object or dict."""
        return cls(document, page=page)

    @classmethod
    def from_builder(
        cls,
        builder: Any,
        *,
        page: str | int | None = None,
        expand_reuse: bool = True,
    ) -> "FigureRef":
        """Create a figure reference from an existing ``DocumentBuilder``."""
        return cls(builder, page=page, expand_reuse=expand_reuse)

    @classmethod
    def from_path(
        cls,
        path: str | Path,
        *,
        page: str | int | None = None,
        validate: bool = True,
    ) -> "FigureRef":
        """Create a figure reference from a YAML or JSON FrameGraph file."""
        return cls(Path(path), page=page, validate=validate)

    def load(
        self,
        *,
        layers: str | Sequence[str] | None = None,
        viewbox: BoxLike | None = None,
    ) -> FigureContent:
        """Resolve this reference into selected live objects."""
        return load_figure(self, layers=layers, viewbox=viewbox)


def load_figure(
    source: FigureRef | Any,
    *,
    page: str | int | None = None,
    layers: str | Sequence[str] | None = None,
    viewbox: BoxLike | None = None,
) -> FigureContent:
    """Load one figure page as live object content."""
    ref = source if isinstance(source, FigureRef) else FigureRef(source, page=page)
    page_selector = ref.page if page is None else page
    raw, fallback_height = _document_dict(ref.source, validate=ref.validate, expand_reuse=ref.expand_reuse)
    pages = raw.get("pages") if isinstance(raw, dict) else None
    if not isinstance(pages, list) or not pages:
        raise ValueError("figure source must contain at least one page")
    page_dict = _select_page(pages, page_selector)
    if page_dict.get("mode", "page") != "page":
        raise ValueError("figure import only supports mode='page' sources")

    selected_layers = _layer_ids(layers)
    objects: list[dict[str, Any]] = []
    layer_names: list[str] = []
    for layer in page_dict.get("layers") or []:
        layer_id = layer.get("id")
        if selected_layers is not None and layer_id not in selected_layers:
            continue
        if isinstance(layer_id, str):
            layer_names.append(layer_id)
        for obj in layer.get("objects") or []:
            objects.append(deepcopy(obj))
    if selected_layers is not None:
        missing = selected_layers - set(layer_names)
        if missing:
            names = ", ".join(sorted(missing))
            raise ValueError(f"figure source does not contain layer(s): {names}")

    source_box = _box(viewbox) if viewbox is not None else _canvas_box(page_dict, raw, fallback_height)
    return FigureContent(
        page_id=page_dict.get("id") if isinstance(page_dict.get("id"), str) else None,
        source_box=source_box,
        layers=tuple(layer_names),
        objects=tuple(objects),
        defs=deepcopy(raw.get("defs") or {}),
    )


def place_figure(
    source: FigureRef | Any,
    box: BoxLike,
    *,
    page: str | int | None = None,
    layers: str | Sequence[str] | None = None,
    viewbox: BoxLike | None = None,
    crop: BoxLike | None = None,
    fit: FitMode = "contain",
    align: str = "center",
    decorative: bool | None = True,
    id_prefix: str | None = None,
    clip: bool | BoxLike = False,
    **fields: Any,
) -> FigurePlacement:
    """Place a live figure into ``box`` and return the lowered group object."""
    if viewbox is not None and crop is not None:
        raise ValueError("use either viewbox or crop, not both")
    content = load_figure(source, page=page, layers=layers, viewbox=viewbox or crop)
    sx, sy, sw, sh = content.source_box
    tx, ty, tw, th = _box(box)
    if sw <= 0 or sh <= 0 or tw <= 0 or th <= 0:
        raise ValueError("figure source and target boxes must have positive width and height")
    scale_x, scale_y, drawn_w, drawn_h = _fit(sw, sh, tw, th, fit)
    dx, dy = _align(tx, ty, tw, th, drawn_w, drawn_h, align)
    transform = Mat3.translate(dx, dy) @ Mat3.scale(scale_x, scale_y) @ Mat3.translate(-sx, -sy)

    children = [deepcopy(obj) for obj in content.objects]
    if id_prefix:
        for obj in children:
            _prefix_object_ids(obj, id_prefix)
    if decorative is not None:
        for obj in children:
            obj.setdefault("decorative", decorative)

    style = dict(fields.pop("style", {}) or {})
    existing = style.get("transform")
    base = list(existing) if isinstance(existing, list) else ([existing] if existing else [])
    style["transform"] = base + [transform.transform_fn()]
    if clip:
        style["clip_path"] = {
            "kind": "rect",
            "box": list(content.source_box if clip is True else _box(clip)),
        }

    group = {
        "type": "group",
        "children": children,
        "style": style,
        "meta": {
            "framegraph.figure": {
                "page": content.page_id,
                "layers": list(content.layers),
                "fit": fit,
                "align": align,
                "source_box": list(content.source_box),
                "target_box": [tx, ty, tw, th],
            }
        },
        **fields,
    }
    if decorative is not None:
        group["decorative"] = decorative
    return FigurePlacement(
        group=group,
        source_box=content.source_box,
        target_box=(tx, ty, tw, th),
        drawn_box=(dx, dy, drawn_w, drawn_h),
        transform=transform,
        defs=content.defs,
    )


def merge_figure_defs(target_doc: dict[str, Any], defs: dict[str, Any]) -> None:
    """Merge imported figure definitions into a target document."""
    if not defs:
        return
    target_defs = target_doc.setdefault("defs", {})
    _merge_mapping(target_defs, defs, path="defs")


def _document_dict(source: Any, *, validate: bool, expand_reuse: bool) -> tuple[dict[str, Any], float | None]:
    fallback_height: float | None = None
    if callable(source):
        from framegraph.sdk.author import DocumentBuilder

        builder = DocumentBuilder()
        returned = source(builder)
        if isinstance(returned, (int, float)):
            fallback_height = float(returned)
        return builder.build_dict(expand_reuse=expand_reuse), fallback_height
    if hasattr(source, "build_dict"):
        return source.build_dict(expand_reuse=expand_reuse), None
    if isinstance(source, (str, Path)):
        parsed = parse(Path(source).read_text(encoding="utf-8"), validate=validate, forgiving=not validate)
        return _as_document_dict(parsed), None
    return _as_document_dict(source), None


def _as_document_dict(value: Any) -> dict[str, Any]:
    data = to_plain_dict(value)
    if isinstance(data, dict) and "pages" in data:
        return data
    if isinstance(data, dict) and "layers" in data:
        return {"dsl": "FrameGraph", "version": HEAD_VERSION, "pages": [data]}
    raise ValueError("figure source must be a FrameGraph document or page")


def _select_page(pages: list[Any], selector: str | int | None) -> dict[str, Any]:
    if selector is None:
        selected = pages[0]
    elif isinstance(selector, int):
        try:
            selected = pages[selector]
        except IndexError as exc:
            raise ValueError(f"figure page index out of range: {selector}") from exc
    else:
        selected = next((page for page in pages if isinstance(page, dict) and page.get("id") == selector), None)
        if selected is None:
            raise ValueError(f"figure source does not contain page {selector!r}")
    if not isinstance(selected, dict):
        raise ValueError("selected figure page is not an object")
    return selected


def _layer_ids(layers: str | Sequence[str] | None) -> set[str] | None:
    if layers is None:
        return None
    if isinstance(layers, str):
        return {layers}
    return {str(layer) for layer in layers}


def _canvas_box(page: dict[str, Any], document: dict[str, Any], fallback_height: float | None) -> tuple[float, float, float, float]:
    canvas = page.get("canvas")
    if canvas is None and page.get("master"):
        master = ((document.get("defs") or {}).get("masters") or {}).get(page["master"])
        if isinstance(master, dict):
            canvas = master.get("canvas")
    if isinstance(canvas, dict) and isinstance(canvas.get("size"), list) and len(canvas["size"]) >= 2:
        return (0.0, 0.0, float(canvas["size"][0]), float(canvas["size"][1]))
    if isinstance(fallback_height, (int, float)):
        return (0.0, 0.0, _infer_width(page), float(fallback_height))
    raise ValueError("figure source needs a canvas size or explicit viewbox")


def _infer_width(page: dict[str, Any]) -> float:
    max_x = 0.0
    for layer in page.get("layers") or []:
        for obj in layer.get("objects") or []:
            box = obj.get("box") if isinstance(obj, dict) else None
            if isinstance(box, list) and len(box) >= 4:
                max_x = max(max_x, float(box[0]) + float(box[2]))
    return max_x or 1.0


def _box(value: BoxLike) -> tuple[float, float, float, float]:
    if len(value) != 4:
        raise ValueError("box must be [x, y, w, h]")
    return (float(value[0]), float(value[1]), float(value[2]), float(value[3]))


def _fit(sw: float, sh: float, tw: float, th: float, fit: FitMode) -> tuple[float, float, float, float]:
    if fit == "stretch":
        return tw / sw, th / sh, tw, th
    if fit == "native":
        scale = 1.0
    elif fit == "cover":
        scale = max(tw / sw, th / sh)
    elif fit == "scale-down":
        scale = min(1.0, min(tw / sw, th / sh))
    elif fit == "contain":
        scale = min(tw / sw, th / sh)
    else:
        raise ValueError(f"unsupported figure fit: {fit!r}")
    return scale, scale, sw * scale, sh * scale


def _align(
    tx: float,
    ty: float,
    tw: float,
    th: float,
    drawn_w: float,
    drawn_h: float,
    align: str,
) -> tuple[float, float]:
    parts = {part.strip() for part in align.replace("_", "-").split("-") if part.strip()}
    if not parts or "center" in parts:
        ax = tx + (tw - drawn_w) / 2
        ay = ty + (th - drawn_h) / 2
    else:
        ax = tx
        ay = ty
    if "left" in parts:
        ax = tx
    elif "right" in parts:
        ax = tx + tw - drawn_w
    elif "center" in parts or not ({"left", "right"} & parts):
        ax = tx + (tw - drawn_w) / 2
    if "top" in parts:
        ay = ty
    elif "bottom" in parts:
        ay = ty + th - drawn_h
    elif "center" in parts or not ({"top", "bottom"} & parts):
        ay = ty + (th - drawn_h) / 2
    unknown = parts - {"center", "left", "right", "top", "bottom"}
    if unknown:
        raise ValueError(f"unsupported figure align value: {align!r}")
    return ax, ay


def _prefix_object_ids(obj: Any, prefix: str) -> None:
    if isinstance(obj, dict):
        if isinstance(obj.get("id"), str):
            obj["id"] = f"{prefix}{obj['id']}"
        for value in obj.values():
            _prefix_object_ids(value, prefix)
    elif isinstance(obj, list):
        for value in obj:
            _prefix_object_ids(value, prefix)


def _merge_mapping(target: dict[str, Any], source: dict[str, Any], *, path: str) -> None:
    for key, value in source.items():
        if key not in target:
            target[key] = deepcopy(value)
            continue
        existing = target[key]
        if isinstance(existing, dict) and isinstance(value, dict):
            _merge_mapping(existing, value, path=f"{path}.{key}")
            continue
        if existing != value:
            raise ValueError(f"conflicting imported figure definition at {path}.{key}")


__all__ = ["FigureContent", "FigurePlacement", "FigureRef", "load_figure", "merge_figure_defs", "place_figure"]
