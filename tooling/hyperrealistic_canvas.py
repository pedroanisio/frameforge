#!/usr/bin/env python3
"""Flatten embedded-SVG canvas layers into one richly colored FrameForge render.

The input shape this targets is a FrameForge canvas whose visual detail lives in
``type: image`` objects with ``data:image/svg+xml`` sources. The script decodes
those embedded SVG layers, lowers their polygons/polylines into native
FrameForge objects, assigns stable ``region.<layer>.<index>`` IDs, applies
deterministic depth/lighting colors, and writes:

* ``*-hyperrealistic.fg.yaml`` - editable native FrameForge document
* ``*-hyperrealistic.svg`` - one rendered SVG with ``id``/``data-region-id``
* ``*-hyperrealistic.summary.json`` - counts and output metadata

Example:

    uv run python tooling/hyperrealistic_canvas.py "canvas.fg (2).yaml" \
        --out-dir out/hyperrealistic-canvas --name canvas-hyperrealistic
"""
from __future__ import annotations

import argparse
import colorsys
import json
import math
import os
import re
import sys
from dataclasses import dataclass
from html import escape
from pathlib import Path
from typing import Any

import yaml


HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))
sys.path[:0] = [ROOT, os.path.join(ROOT, "src"), os.path.join(ROOT, "docs")]

from frameforge.rendering.application.renderer import Renderer  # noqa: E402
from frameforge.sdk.region import object_bbox  # noqa: E402
from frameforge.vision.infrastructure.svg_import import svg_to_objects  # noqa: E402


@dataclass(frozen=True)
class SourceLayer:
    id: str
    box: list[float]
    src: str


@dataclass(frozen=True)
class HyperrealisticResult:
    document: dict[str, Any]
    summary: dict[str, Any]
    object_ids: list[str]


def _default_name(path: Path) -> str:
    stem = path.stem
    if stem.endswith(".fg"):
        stem = stem[:-3]
    return f"{stem}-hyperrealistic"


def _parse_canvas_source(path: Path) -> tuple[dict[str, Any], list[SourceLayer]]:
    """Extract only the canvas envelope and embedded image layers.

    ``canvas.fg (2).yaml`` is tens of megabytes because the SVGs are URL-encoded
    on single lines. A streaming parser is much faster and uses less memory than
    loading the whole file through PyYAML just to reach those payloads.
    """
    title = "Hyperrealistic canvas"
    lang = "en"
    size: list[float] = []
    units = "px"
    in_size = False
    current: dict[str, Any] | None = None
    in_box = False
    layers: list[SourceLayer] = []

    def finish_current() -> None:
        nonlocal current
        if not current:
            return
        if current.get("id") and len(current.get("box", [])) == 4 and current.get("src"):
            src = str(current["src"])
            if src.startswith("data:image/svg+xml"):
                layers.append(SourceLayer(str(current["id"]), list(current["box"]), src))
        current = None

    with path.open("r", encoding="utf-8") as fh:
        for raw in fh:
            s = raw.strip()
            if s.startswith("title:"):
                title = s.split(":", 1)[1].strip().strip("'\"") or title
            elif s.startswith("lang:"):
                lang = s.split(":", 1)[1].strip().strip("'\"") or lang
            elif s == "size:" and current is None:
                in_size = True
                size = []
            elif in_size and s.startswith("- "):
                try:
                    size.append(float(s[2:].strip()))
                except ValueError:
                    in_size = False
                if len(size) == 2:
                    in_size = False
            elif s.startswith("units:") and current is None:
                units = s.split(":", 1)[1].strip().strip("'\"") or units

            if s == "- type: image":
                finish_current()
                current = {"box": []}
                in_box = False
                continue
            if current is None:
                continue
            if s.startswith("id:"):
                current["id"] = s.split(":", 1)[1].strip().strip("'\"")
            elif s == "box:":
                in_box = True
            elif in_box and s.startswith("- "):
                try:
                    current["box"].append(float(s[2:].strip()))
                except ValueError:
                    in_box = False
                if len(current["box"]) == 4:
                    in_box = False
            elif s.startswith("src:"):
                current["src"] = s.split(":", 1)[1].strip()
        finish_current()

    if len(size) != 2:
        # Fall back to the largest declared layer extent.
        max_w = max((layer.box[0] + layer.box[2] for layer in layers), default=1080.0)
        max_h = max((layer.box[1] + layer.box[3] for layer in layers), default=1080.0)
        size = [float(max_w), float(max_h)]

    return {"title": title, "lang": lang, "size": size, "units": units}, layers


def _clamp(v: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return min(hi, max(lo, v))


def _hex_to_rgb(color: str) -> tuple[int, int, int]:
    h = color.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def _rgb_to_hex(rgb: tuple[float, float, float]) -> str:
    return "#" + "".join(f"{int(_clamp(c / 255.0) * 255):02x}" for c in rgb)


def _mix(a: str, b: str, t: float) -> str:
    t = _clamp(t)
    ar, ag, ab = _hex_to_rgb(a)
    br, bg, bb = _hex_to_rgb(b)
    return _rgb_to_hex((
        ar * (1 - t) + br * t,
        ag * (1 - t) + bg * t,
        ab * (1 - t) + bb * t,
    ))


def _hsl(h: float, s: float, light: float) -> str:
    r, g, b = colorsys.hls_to_rgb((h % 360.0) / 360.0, _clamp(light), _clamp(s))
    return _rgb_to_hex((r * 255, g * 255, b * 255))


def _color_triplet(layer_index: int, obj_index: int, bbox: tuple[float, float, float, float],
                   canvas: list[float]) -> tuple[str, str, str]:
    x1, y1, x2, y2 = bbox
    width = max(float(canvas[0]), 1.0)
    height = max(float(canvas[1]), 1.0)
    cx = _clamp(((x1 + x2) / 2.0) / width)
    cy = _clamp(((y1 + y2) / 2.0) / height)
    hue_bases = [28, 172, 212, 320, 47, 260, 8]
    hue = hue_bases[layer_index % len(hue_bases)] + 34.0 * cx + 13.0 * math.sin(obj_index * 0.37)
    light = 0.32 + 0.34 * (1.0 - cy) + 0.08 * math.sin((cx + cy + obj_index) * 2.1)
    sat = 0.48 + 0.22 * math.sin(layer_index + obj_index * 0.11) ** 2
    base = _hsl(hue, sat, light)
    high = _mix(base, "#fff4ce", 0.42 + 0.22 * (1.0 - cy))
    low = _mix(base, "#07111d", 0.44 + 0.18 * cy)
    return low, base, high


def _linear_gradient(low: str, base: str, high: str, angle: float) -> dict[str, Any]:
    return {
        "kind": "linear",
        "angle": round(angle, 2),
        "stops": [
            {"position": "0%", "color": low},
            {"position": "48%", "color": base},
            {"position": "100%", "color": high},
        ],
    }


def _background_objects(width: float, height: float) -> list[dict[str, Any]]:
    return [
        {
            "type": "rect",
            "id": "region.background.deep_atmosphere",
            "box": [0, 0, width, height],
            "fill": _linear_gradient("#0a1018", "#24364a", "#f3d49a", 34),
        },
        {
            "type": "ellipse",
            "id": "region.background.warm_key_light",
            "center": [width * 0.28, height * 0.18],
            "rx": width * 0.56,
            "ry": height * 0.42,
            "fill": {
                "kind": "radial",
                "shape": "circle",
                "at": "50% 50%",
                "stops": [
                    {"position": "0%", "color": "#fff0b8"},
                    {"position": "55%", "color": "#d48a54"},
                    {"position": "100%", "color": "#24364a"},
                ],
            },
            "opacity": 0.24,
            "effects": [{"kind": "glow", "blur": 18, "color": "#ffe7a3", "opacity": 0.24}],
        },
    ]


def _style_object(obj: dict[str, Any], *, region_id: str, layer_id: str, layer_index: int,
                  obj_index: int, canvas: list[float]) -> dict[str, Any]:
    styled = dict(obj)
    if styled.get("type") == "polygon":
        points = styled.get("points") or []
        styled["type"] = "polyline"
        if len(points) >= 3:
            styled["closed"] = True
    bbox = object_bbox(styled) or (0.0, 0.0, canvas[0], canvas[1])
    low, base, high = _color_triplet(layer_index, obj_index, bbox, canvas)
    angle = 22.0 + layer_index * 19.0 + (obj_index % 11) * 3.5

    styled["id"] = region_id
    styled["meta"] = {
        "region": {
            "id": region_id,
            "source_layer": layer_id,
            "source_index": obj_index,
            "bbox": [round(float(v), 3) for v in bbox],
        }
    }
    styled["z"] = layer_index * 10000 + obj_index
    styled["stroke"] = _mix(base, "#f8fbff", 0.28)
    stroke_style = dict(styled.get("stroke_style") or {})
    stroke_style["stroke_width"] = round(float(stroke_style.get("stroke_width", 1.0)) * 1.08, 3)
    stroke_style["stroke_linecap"] = "round"
    stroke_style["stroke_linejoin"] = "round"
    styled["stroke_style"] = stroke_style
    styled["stroke_opacity"] = 0.78

    if styled.get("type") == "polyline" and styled.get("closed"):
        styled["fill"] = _linear_gradient(low, base, high, angle)
        styled["fill_opacity"] = 0.56
        styled["effects"] = [
            {"kind": "shadow", "dx": 1.4, "dy": 2.1, "blur": 4.8,
             "color": "#03070c", "opacity": 0.18},
            {"kind": "glow", "blur": 1.6, "color": high, "opacity": 0.18},
        ]
    else:
        styled["fill"] = "none"
        styled["effects"] = [
            {"kind": "glow", "blur": 1.15, "color": high, "opacity": 0.22},
        ]
    return styled


def build_hyperrealistic_document(source: str | Path) -> HyperrealisticResult:
    source_path = Path(source)
    canvas, source_layers = _parse_canvas_source(source_path)
    width, height = (float(canvas["size"][0]), float(canvas["size"][1]))
    region_objects: list[dict[str, Any]] = []
    layer_counts: dict[str, int] = {}

    for layer_index, layer in enumerate(source_layers):
        # svg_to_objects accepts data:image/svg+xml URIs directly (SDK ingest).
        imported = svg_to_objects(layer.src, box=layer.box, data_attrs=True)
        layer_counts[layer.id] = len(imported)
        for idx, obj in enumerate(imported, 1):
            region_id = f"region.{layer.id}.{idx:04d}"
            region_objects.append(
                _style_object(
                    obj,
                    region_id=region_id,
                    layer_id=layer.id,
                    layer_index=layer_index,
                    obj_index=idx,
                    canvas=[width, height],
                )
            )

    background = _background_objects(width, height)
    document = {
        "dsl": "FrameForge",
        "version": "2.5.0",
        "profile": "diagram",
        "title": f"Hyperrealistic colored rendering - {canvas['title']}",
        "lang": canvas["lang"],
        "pages": [
            {
                "mode": "page",
                "id": "hyperrealistic-canvas",
                "canvas": {"size": [width, height], "units": canvas["units"]},
                "rendering": {"coordinate_mode": "absolute"},
                "layers": [
                    {"id": "atmosphere", "objects": background},
                    {"id": "id-regions", "objects": region_objects},
                ],
            }
        ],
    }
    object_ids = ["region.background.page"] + [obj["id"] for obj in background + region_objects]
    summary = {
        "source": str(source_path),
        "source_layers": len(source_layers),
        "source_layer_objects": layer_counts,
        "region_objects": len(region_objects),
        "background_objects": len(background) + 1,
        "document_background_objects": len(background),
        "total_rendered_objects": len(object_ids),
        "canvas": {"width": width, "height": height, "units": canvas["units"]},
    }
    return HyperrealisticResult(document=document, summary=summary, object_ids=object_ids)


_PRIMITIVE_RE = re.compile(r"<(rect|ellipse|circle|polygon|polyline|path|line)(?=[\s>/])")


def add_svg_region_ids(svg: str, object_ids: list[str]) -> tuple[str, int]:
    ids = iter(object_ids)
    assigned = 0

    def repl(match: re.Match[str]) -> str:
        nonlocal assigned
        try:
            region_id = next(ids)
        except StopIteration:
            return match.group(0)
        assigned += 1
        attr = f' id="{escape(region_id, quote=True)}" data-region-id="{escape(region_id, quote=True)}"'
        return f"<{match.group(1)}{attr}"

    return _PRIMITIVE_RE.sub(repl, svg), assigned


def render_svg(document: dict[str, Any], *, base_dir: Path | None = None) -> str:
    renderer = Renderer(document, str(base_dir or Path.cwd()))
    page = document["pages"][0]
    svgs = list(renderer.render_page(page))
    if not svgs:
        raise RuntimeError("renderer produced no SVG pages")
    return svgs[0]


def write_outputs(result: HyperrealisticResult, *, source: Path, out_dir: Path,
                  name: str | None = None) -> dict[str, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    base = name or _default_name(source)
    yaml_path = out_dir / f"{base}.fg.yaml"
    svg_path = out_dir / f"{base}.svg"
    summary_path = out_dir / f"{base}.summary.json"

    yaml_path.write_text(
        yaml.safe_dump(result.document, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )
    svg = render_svg(result.document, base_dir=source.parent)
    svg, assigned = add_svg_region_ids(svg, result.object_ids)
    svg_path.write_text(svg, encoding="utf-8")

    summary = dict(result.summary)
    summary["outputs"] = {
        "yaml": str(yaml_path),
        "svg": str(svg_path),
        "summary": str(summary_path),
    }
    summary["svg_region_ids_assigned"] = assigned
    if assigned != len(result.object_ids):
        summary["warning"] = (
            f"assigned {assigned} SVG ids for {len(result.object_ids)} document objects; "
            "inspect the SVG before relying on every region id"
        )
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return {"yaml": yaml_path, "svg": svg_path, "summary": summary_path}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("source", help="FrameForge YAML containing embedded SVG image layers")
    parser.add_argument("--out-dir", default="out/hyperrealistic-canvas",
                        help="directory for generated YAML/SVG/summary artifacts")
    parser.add_argument("--name", default=None,
                        help="base output filename without extension")
    args = parser.parse_args(argv)

    source = Path(args.source)
    result = build_hyperrealistic_document(source)
    outputs = write_outputs(result, source=source, out_dir=Path(args.out_dir), name=args.name)
    print(
        f"converted {result.summary['source_layers']} layer(s), "
        f"{result.summary['region_objects']} region object(s)"
    )
    for label, path in outputs.items():
        print(f"  wrote {label}: {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
