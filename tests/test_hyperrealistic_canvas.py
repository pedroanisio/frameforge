from __future__ import annotations

import importlib.util
import sys
import urllib.parse
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tooling" / "hyperrealistic_canvas.py"


def _load_tool():
    spec = importlib.util.spec_from_file_location("hyperrealistic_canvas", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _sample_doc(tmp_path: Path) -> Path:
    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" width="20" height="10" '
        'viewBox="0 0 20 10">'
        '<polygon points="1,1 18,1 10,8" fill="none" stroke="#7c74ff" '
        'stroke-width="1"/>'
        '<polyline points="2,9 8,5 18,9" fill="none" stroke="#7c74ff" '
        'stroke-width="1"/>'
        "</svg>"
    )
    uri = "data:image/svg+xml;charset=utf-8," + urllib.parse.quote(svg)
    path = tmp_path / "sample.fg.yaml"
    path.write_text(
        "\n".join(
            [
                "dsl: FrameForge",
                "version: 2.2.0",
                "profile: diagram",
                "title: Sample canvas",
                "lang: en",
                "pages:",
                "- mode: page",
                "  id: canvas",
                "  canvas:",
                "    size:",
                "    - 100.0",
                "    - 80.0",
                "    units: px",
                "  rendering:",
                "    coordinate_mode: absolute",
                "  layers:",
                "  - id: main",
                "    objects:",
                "    - type: rect",
                "      box:",
                "      - 0.0",
                "      - 0.0",
                "      - 100.0",
                "      - 80.0",
                "      fill: '#ffffff'",
                "    - type: image",
                "      id: layer_0",
                "      box:",
                "      - 10.0",
                "      - 20.0",
                "      - 40.0",
                "      - 20.0",
                f"      src: {uri}",
                "      alt: vectors",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return path


def test_build_document_flattens_embedded_svg_layers(tmp_path):
    tool = _load_tool()
    source = _sample_doc(tmp_path)

    result = tool.build_hyperrealistic_document(source)
    doc = result.document
    region_objects = doc["pages"][0]["layers"][1]["objects"]

    assert result.summary["source_layers"] == 1
    assert result.summary["region_objects"] == 2
    assert all(obj["type"] != "image" for obj in region_objects)
    assert region_objects[0]["id"] == "region.layer_0.0001"
    assert region_objects[0]["meta"]["region"]["source_layer"] == "layer_0"
    assert region_objects[0]["fill"] != "none"
    assert region_objects[1]["stroke"] != "#7c74ff"


def test_main_writes_yaml_svg_and_summary_with_svg_region_ids(tmp_path):
    tool = _load_tool()
    source = _sample_doc(tmp_path)
    out_dir = tmp_path / "out"

    assert tool.main([str(source), "--out-dir", str(out_dir)]) == 0

    yaml_out = out_dir / "sample-hyperrealistic.fg.yaml"
    svg_out = out_dir / "sample-hyperrealistic.svg"
    summary_out = out_dir / "sample-hyperrealistic.summary.json"

    assert yaml_out.exists()
    assert svg_out.exists()
    assert summary_out.exists()
    rendered = svg_out.read_text(encoding="utf-8")
    assert 'id="region.layer_0.0001"' in rendered
    assert 'data-region-id="region.layer_0.0002"' in rendered
    assert "data:image/svg+xml" not in yaml_out.read_text(encoding="utf-8")
