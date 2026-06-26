"""SVG → FrameGraph object importer (the ingestion back-end).

Lowers an SVG document into FrameGraph primitive object dicts (``rect`` /
``ellipse`` / ``line`` / ``polyline`` / ``polygon`` / ``path``) that the renderer
draws 1:1. This is the universal entry point for vector ingestion: anything that
emits SVG — the raster vectorizer, Inkscape, Illustrator, VTracer — flows in here.

Dependency-free (stdlib ``xml`` only); emits plain dicts, imports no framegraph
model, so it stays a leaf the package boundary is happy with.

Honest limits: handles solid ``fill``/``stroke`` (with group inheritance),
``transform`` passthrough, and an optional box-fit scale. It does NOT resolve
gradient/pattern paints (``url(#…)`` falls back to a neutral grey), ``<use>``,
``clipPath``, ``mask``, CSS ``<style>`` rules, or ``<text>`` — those need the
richer pipeline (segmentation/OCR) layered on top.
"""
from __future__ import annotations

import math
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Optional, Sequence

_NUM = r"[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?"
_FILL_SHAPES = {"rect", "circle", "ellipse", "polygon", "path"}
_FALLBACK_FILL = "#C7CCD6"
_URL_REF = re.compile(r"url\(\s*['\"]?#([^)'\"]+)['\"]?\s*\)")


def _localname(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _load(svg: "str | Path") -> str:
    if isinstance(svg, Path):
        return svg.read_text(encoding="utf-8")
    s = str(svg)
    if s.lstrip().startswith("<"):
        return s
    return Path(s).read_text(encoding="utf-8")


def _f(v: Optional[str], default: float = 0.0) -> float:
    if v is None:
        return default
    m = re.match(_NUM, v.strip())
    return float(m.group()) if m else default


def _viewbox(root) -> Optional[tuple[float, float, float, float]]:
    vb = root.get("viewBox")
    if vb:
        p = [float(x) for x in re.split(r"[ ,]+", vb.strip()) if x]
        if len(p) == 4:
            return (p[0], p[1], p[2], p[3])
    w, h = root.get("width"), root.get("height")
    if w and h:
        return (0.0, 0.0, _f(w), _f(h))
    return None


def _points(s: str) -> list[list[float]]:
    nums = [float(x) for x in re.findall(_NUM, s or "")]
    return [[nums[i], nums[i + 1]] for i in range(0, len(nums) - 1, 2)]


def _hex_rgb(h: str) -> tuple[int, int, int]:
    h = h.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def _stop_position(offset: Optional[str]) -> str:
    """SVG ``offset`` (``0``..``1`` or ``%``) → FrameGraph ``position`` percentage."""
    o = (offset or "0").strip()
    if o.endswith("%"):
        return o
    v = _f(o, 0.0)
    return f"{(v * 100 if v <= 1 else v):g}%"


def _stop_color(stop) -> str:
    color = (stop.get("stop-color") or "#000000").strip()
    op = stop.get("stop-opacity")
    if op is not None:
        alpha = _f(op, 1.0)
        if alpha < 1.0 and color.startswith("#"):
            r, g, b = _hex_rgb(color)
            return f"rgba({r},{g},{b},{alpha:g})"
    return color


def _gradient_to_fg(el) -> Optional[dict[str, Any]]:
    """Convert an SVG ``<linear/radialGradient>`` to a FrameGraph ``Gradient`` paint.

    Honest limits: ``userSpaceOnUse`` coordinates are reduced to a CSS gradient line
    (a direction ``angle`` for linear; a centred ``at`` for radial), which matches
    when the gradient vector spans the painted region — the raster-fit-per-region
    case. ``xlink:href`` stop inheritance and ``gradientTransform`` are not resolved.
    """
    stops = [{"color": _stop_color(s), "position": _stop_position(s.get("offset"))}
             for s in el if _localname(s.tag) == "stop"]
    if not stops:
        return None
    if _localname(el.tag) == "radialGradient":
        return {"kind": "radial", "stops": stops, "at": "50% 50%", "shape": "circle"}
    x1, y1 = _f(el.get("x1"), 0.0), _f(el.get("y1"), 0.0)
    x2, y2 = _f(el.get("x2"), 1.0), _f(el.get("y2"), 0.0)
    angle = math.degrees(math.atan2(x2 - x1, -(y2 - y1))) % 360.0   # 0=up, 90=right (CSS)
    return {"kind": "linear", "stops": stops, "angle": round(angle, 2)}


def _collect_gradients(root) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for el in root.iter():
        if _localname(el.tag) in ("linearGradient", "radialGradient"):
            gid = el.get("id")
            if not gid:
                continue
            grad = _gradient_to_fg(el)
            if grad is not None:
                out[gid] = grad
    return out


def _clean_paint(value: Optional[str], gradients: dict[str, dict[str, Any]]) -> Any:
    if value is None:
        return None
    v = value.strip()
    m = _URL_REF.match(v)
    if m:                              # url(#id): resolve a known gradient, else fall back
        return gradients.get(m.group(1), _FALLBACK_FILL)
    if v.startswith("url("):
        return _FALLBACK_FILL          # patterns / unparsable refs can't resolve here
    return v


def _emit(name: str, el) -> Optional[dict[str, Any]]:
    if name == "rect":
        obj: dict[str, Any] = {"type": "rect",
                               "box": [_f(el.get("x")), _f(el.get("y")),
                                       _f(el.get("width")), _f(el.get("height"))]}
        r = el.get("rx") or el.get("ry")
        if r:
            obj["radius"] = _f(r)
        return obj
    if name == "circle":
        r = _f(el.get("r"))
        return {"type": "ellipse", "center": [_f(el.get("cx")), _f(el.get("cy"))], "rx": r, "ry": r}
    if name == "ellipse":
        return {"type": "ellipse", "center": [_f(el.get("cx")), _f(el.get("cy"))],
                "rx": _f(el.get("rx")), "ry": _f(el.get("ry"))}
    if name == "line":
        return {"type": "line", "from": [_f(el.get("x1")), _f(el.get("y1"))],
                "to": [_f(el.get("x2")), _f(el.get("y2"))]}
    if name == "polyline":
        return {"type": "polyline", "points": _points(el.get("points", ""))}
    if name == "polygon":
        return {"type": "polygon", "points": _points(el.get("points", ""))}
    if name == "path" and el.get("d"):
        return {"type": "path", "d": el.get("d")}
    return None


def _apply_paint(obj: dict[str, Any], name: str, fill, stroke, sw, gradients) -> None:
    fill = _clean_paint(fill, gradients)
    stroke = _clean_paint(stroke, gradients)
    if name in _FILL_SHAPES:
        obj["fill"] = fill if fill is not None else "#000000"   # SVG default fill is black
    if stroke and stroke != "none":
        obj["stroke"] = stroke
        obj["stroke_style"] = {"stroke_width": _f(sw, 1.0)}


def svg_to_objects(svg: "str | Path", *, box: Optional[Sequence[float]] = None,
                   data_attrs: bool = False) -> list[dict[str, Any]]:
    """Return FrameGraph object dicts for every drawable element in ``svg``.

    ``svg`` is SVG text or a path to a ``.svg`` file. ``box`` (``[x, y, w, h]``),
    when given, fits the document's viewBox into that box (centered, aspect
    preserved) via a ``style.transform`` applied to every object; element/group
    ``transform`` attributes are composed on top.

    ``data_attrs`` (opt-in) carries an element's ``data-*`` attributes onto the
    emitted object as ``meta['data']`` (keyed without the ``data-`` prefix), so
    upstream semantics — e.g. ``data-class="foreground"`` from a segmenting
    rebuild — survive ingestion and can drive region selection. Only leaf
    (drawable) elements are carried; ``data-*`` on a ``<g>`` is not propagated.
    Default ``False`` keeps the output byte-identical to a plain ingest.
    """
    root = ET.fromstring(_load(svg))
    gradients = _collect_gradients(root)
    vb = _viewbox(root)
    boxfit = ""
    if box is not None and vb is not None:
        vx, vy, vw, vh = vb
        bx, by, bw, bh = box
        s = min(bw / vw, bh / vh) if vw and vh else 1.0
        tx = bx + (bw - vw * s) / 2 - vx * s
        ty = by + (bh - vh * s) / 2 - vy * s
        boxfit = f"translate({tx:.3f} {ty:.3f}) scale({s:.5f})"

    out: list[dict[str, Any]] = []

    def walk(el, inh: dict[str, Any]) -> None:
        name = _localname(el.tag)
        cur = {
            "fill": el.get("fill", inh["fill"]),
            "stroke": el.get("stroke", inh["stroke"]),
            "sw": el.get("stroke-width", inh["sw"]),
            "tr": inh["tr"] + ([el.get("transform")] if el.get("transform") else []),
        }
        if name in ("svg", "g", "a"):
            for child in el:
                walk(child, cur)
            return
        obj = _emit(name, el)
        if obj is None:
            for child in el:
                walk(child, cur)
            return
        _apply_paint(obj, name, cur["fill"], cur["stroke"], cur["sw"], gradients)
        if data_attrs:
            data = {k[5:]: v for k, v in el.attrib.items() if k.startswith("data-")}
            if data:
                obj["meta"] = {"data": data}
        parts = ([boxfit] if boxfit else []) + cur["tr"]
        if parts:
            obj["style"] = {"transform": " ".join(parts)}
        out.append(obj)

    walk(root, {"fill": None, "stroke": None, "sw": None, "tr": []})
    return out
