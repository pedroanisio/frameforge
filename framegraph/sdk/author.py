"""Authoring builders for the Python SDK."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from framegraph.sdk.expand import ExpandOptions, expand
from framegraph.sdk.model import HEAD_VERSION, validate_document


@dataclass(frozen=True)
class Handle:
    """Nominal reference returned by definition helpers."""

    kind: str
    name: str

    def __str__(self) -> str:
        return self.name


class DocumentBuilder:
    """Small fluent builder that lowers directly to the authoritative model."""

    def __init__(
        self,
        *,
        title: str | None = None,
        profile: str | None = None,
        lang: str | None = None,
        version: str = HEAD_VERSION,
    ) -> None:
        self._doc: dict[str, Any] = {"dsl": "FrameGraph", "version": version, "pages": []}
        if title is not None:
            self._doc["title"] = title
        if profile is not None:
            self._doc["profile"] = profile
        if lang is not None:
            self._doc["lang"] = lang

    def define_color(self, name: str, value: str) -> Handle:
        self._tokens("colors")[name] = value
        return Handle("color", name)

    def define_font(self, name: str, *, family: str, src: str | None = None, hash: str | None = None, **fields: Any) -> Handle:
        font: dict[str, Any] = {"family": family}
        if src is not None:
            font["src"] = src
        if hash is not None:
            font["hash"] = hash
        font.update(fields)
        self._tokens("fonts")[name] = font
        return Handle("font", name)

    def define_style(self, name: str, **style: Any) -> Handle:
        self._tokens("styles")[name] = _coerce_handles(style)
        return Handle("style", name)

    def define_text_style(self, name: str, **style: Any) -> Handle:
        self._tokens("text_styles")[name] = _coerce_handles(style)
        return Handle("text_style", name)

    def define_stroke_style(self, name: str, **style: Any) -> Handle:
        self._tokens("stroke_styles")[name] = _coerce_handles(style)
        return Handle("stroke_style", name)

    def define_asset(self, name: str, src: str, *, kind: str | None = None, hash: str | None = None, **fields: Any) -> Handle:
        asset: dict[str, Any] = {"src": src}
        if kind is not None:
            asset["kind"] = kind
        if hash is not None:
            asset["hash"] = hash
        asset.update(fields)
        self._defs("assets")[name] = asset
        return Handle("asset", name)

    def define_master(self, name: str, master: dict[str, Any]) -> Handle:
        self._defs("masters")[name] = _coerce_handles(master)
        return Handle("master", name)

    def define_symbol(self, name: str, *, box: list[Any], objects: list[dict[str, Any]], **fields: Any) -> Handle:
        symbol = {"box": box, "objects": _coerce_handles(objects)}
        symbol.update(_coerce_handles(fields))
        self._defs("symbols")[name] = symbol
        return Handle("symbol", name)

    def define_component(self, name: str, spec: dict[str, Any]) -> Handle:
        self._defs("components")[name] = _coerce_handles(spec)
        return Handle("component", name)

    def page(
        self,
        id: str,
        *,
        canvas: str | dict[str, Any] | None = None,
        master: Handle | str | None = None,
        reading_order: list[str] | None = None,
    ) -> "PageBuilder":
        page: dict[str, Any] = {"mode": "page", "id": id, "layers": []}
        if canvas is not None:
            page["canvas"] = _coerce_handles(canvas)
        if master is not None:
            page["master"] = _handle_name(master, {"master"}, "master")
        if reading_order is not None:
            page["reading_order"] = reading_order
        self._doc["pages"].append(page)
        return PageBuilder(page)

    def flow(self, id: str, *, master: Handle | str, story: list[dict[str, Any]], **fields: Any) -> None:
        section: dict[str, Any] = {
            "mode": "flow",
            "id": id,
            "master": _handle_name(master, {"master"}, "master"),
            "story": _coerce_handles(story),
        }
        section.update(_coerce_handles(fields))
        self._doc["pages"].append(section)

    def build_dict(self, *, expand_reuse: bool = True) -> dict[str, Any]:
        if expand_reuse:
            return expand(self._doc, opts=ExpandOptions(pin_assets=False)).document.model_dump(
                by_alias=True,
                exclude_none=True,
            )
        validate_document(self._doc)
        return _coerce_handles(self._doc)

    def build(self, *, expand_reuse: bool = True):
        if expand_reuse:
            return expand(self._doc, opts=ExpandOptions(pin_assets=False)).document
        return validate_document(self._doc)

    def _defs(self, key: str) -> dict[str, Any]:
        defs = self._doc.setdefault("defs", {})
        return defs.setdefault(key, {})

    def _tokens(self, key: str) -> dict[str, Any]:
        defs = self._doc.setdefault("defs", {})
        tokens = defs.setdefault("tokens", {})
        return tokens.setdefault(key, {})


class PageBuilder:
    """Builder for a single page's layers and visual objects."""

    def __init__(self, page: dict[str, Any]) -> None:
        self._page = page
        self._current_layer: dict[str, Any] | None = None

    def layer(self, id: str, **fields: Any) -> "PageBuilder":
        layer = {"id": id, "objects": []}
        layer.update(_coerce_handles(fields))
        self._page.setdefault("layers", []).append(layer)
        self._current_layer = layer
        return self

    def add(self, obj: dict[str, Any]) -> "PageBuilder":
        self._objects().append(_coerce_handles(obj))
        return self

    def rect(self, box: list[Any], **fields: Any) -> "PageBuilder":
        return self.add({"type": "rect", "box": box, **fields})

    def text(self, box: list[Any], text: str, **fields: Any) -> "PageBuilder":
        return self.add({"type": "text", "box": box, "text": text, **fields})

    def image(self, box: list[Any], src: Handle | str, **fields: Any) -> "PageBuilder":
        return self.add({"type": "image", "box": box, "src": _handle_name(src, {"asset"}, "src"), **fields})

    def line(self, start: list[float], end: list[float], **fields: Any) -> "PageBuilder":
        return self.add({"type": "line", "from": start, "to": end, **fields})

    def group(self, children: list[dict[str, Any]], **fields: Any) -> "PageBuilder":
        return self.add({"type": "group", "children": children, **fields})

    def use(self, symbol: Handle | str, box: list[Any], **fields: Any) -> "PageBuilder":
        return self.add({"type": "use", "symbol": _handle_name(symbol, {"symbol"}, "symbol"), "box": box, **fields})

    def component(self, component: Handle | str, box: list[Any], **fields: Any) -> "PageBuilder":
        return self.add(
            {
                "type": "component",
                "component": _handle_name(component, {"component"}, "component"),
                "box": box,
                **fields,
            }
        )

    def _objects(self) -> list[dict[str, Any]]:
        if self._current_layer is None:
            self.layer("main")
        assert self._current_layer is not None
        return self._current_layer.setdefault("objects", [])


def _coerce_handles(value: Any, field: str | None = None) -> Any:
    if isinstance(value, Handle):
        _check_handle(value, _allowed_handle_kinds(field), field or "value")
        return value.name
    if isinstance(value, dict):
        return {k: _coerce_handles(v, str(k)) for k, v in value.items()}
    if isinstance(value, list):
        return [_coerce_handles(v, field) for v in value]
    if isinstance(value, tuple):
        return tuple(_coerce_handles(v, field) for v in value)
    return value


def _handle_name(value: Handle | str, allowed: set[str], field: str) -> str:
    if isinstance(value, Handle):
        _check_handle(value, allowed, field)
        return value.name
    return str(value)


def _check_handle(handle: Handle, allowed: set[str], field: str) -> None:
    if allowed and handle.kind not in allowed:
        expected = ", ".join(sorted(allowed))
        raise TypeError(f"{field} expects handle kind {expected}; got {handle.kind}")


def _allowed_handle_kinds(field: str | None) -> set[str]:
    if field == "master":
        return {"master"}
    if field in {"src", "asset"}:
        return {"asset"}
    if field in {"symbol"}:
        return {"symbol"}
    if field in {"component"}:
        return {"component"}
    if field == "style":
        return {"style", "text_style"}
    if field == "stroke_style":
        return {"stroke_style"}
    if field in {"fill", "stroke", "color", "marker_color"}:
        return {"color"}
    if field in {"font", "font_family"}:
        return {"font"}
    return set()


__all__ = ["DocumentBuilder", "Handle", "PageBuilder"]
