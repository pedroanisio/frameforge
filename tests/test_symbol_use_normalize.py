from pathlib import Path
import sys

import yaml


ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT), str(ROOT / "src"), str(ROOT / "docs")]

from tooling.render_fixtures import Renderer, normalize_doc  # noqa: E402


def test_page_based_docs_expand_defs_symbols_before_rendering():
    path = ROOT / "tests" / "fixtures" / "newset" / "faz-ai-manifesto-deck.v2.fg.yaml"
    doc = normalize_doc(yaml.safe_load(path.read_text()))
    use_count = 0

    def visit(obj):
        nonlocal use_count
        if not isinstance(obj, dict):
            return
        if obj.get("type") == "use":
            use_count += 1
        for child in obj.get("children") or []:
            visit(child)

    for page in doc.get("pages") or []:
        for layer in page.get("layers") or []:
            for obj in layer.get("objects") or []:
                visit(obj)

    assert use_count == 0
    renderer = Renderer(doc, str(path.parent))
    svg = renderer.render_page(doc["pages"][0])
    svg = "".join(svg) if isinstance(svg, list) else svg
    assert "?use" not in svg
    assert "faz.ai" in svg


def test_flow_object_symbol_uses_expand_before_rendering():
    doc = normalize_doc({
        "dsl": "FrameForge",
        "version": "2.2.0",
        "defs": {"symbols": {"badge": {"box": [0, 0, 80, 24], "objects": [
            {"type": "rect", "box": [0, 0, 80, 24], "fill": "#fff"},
            {"type": "text", "box": [4, 4, 72, 16], "text": "$label"},
        ]}}},
        "pages": [{"mode": "flow", "id": "p", "story": [{
            "type": "figure",
            "object": {"type": "use", "symbol": "badge", "box": [0, 0, 80, 24], "label": "Embedded"},
        }]}],
    })

    obj = doc["pages"][0]["story"][0]["object"]
    assert obj["type"] == "group"
    assert obj["children"][1]["text"] == "Embedded"
