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

import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Optional, Sequence

_NUM = r"[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?"
_FILL_SHAPES = {"rect", "circle", "ellipse", "polygon", "path"}
_FALLBACK_FILL = "#C7CCD6"


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


def _clean_paint(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    v = value.strip()
    if v.startswith("url("):
        return _FALLBACK_FILL          # gradients/patterns can't resolve here
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


def _apply_paint(obj: dict[str, Any], name: str, fill, stroke, sw) -> None:
    fill = _clean_paint(fill)
    stroke = _clean_paint(stroke)
    if name in _FILL_SHAPES:
        obj["fill"] = fill if fill is not None else "#000000"   # SVG default fill is black
    if stroke and stroke != "none":
        obj["stroke"] = stroke
        obj["stroke_style"] = {"stroke_width": _f(sw, 1.0)}


def svg_to_objects(svg: "str | Path", *, box: Optional[Sequence[float]] = None) -> list[dict[str, Any]]:
    """Return FrameGraph object dicts for every drawable element in ``svg``.

    ``svg`` is SVG text or a path to a ``.svg`` file. ``box`` (``[x, y, w, h]``),
    when given, fits the document's viewBox into that box (centered, aspect
    preserved) via a ``style.transform`` applied to every object; element/group
    ``transform`` attributes are composed on top.
    """
    root = ET.fromstring(_load(svg))
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
        _apply_paint(obj, name, cur["fill"], cur["stroke"], cur["sw"])
        parts = ([boxfit] if boxfit else []) + cur["tr"]
        if parts:
            obj["style"] = {"transform": " ".join(parts)}
        out.append(obj)

    walk(root, {"fill": None, "stroke": None, "sw": None, "tr": []})
    return out
