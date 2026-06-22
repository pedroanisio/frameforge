from pathlib import Path
import sys

import yaml


ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tooling.render_fixtures import Renderer, normalize_doc  # noqa: E402


def test_page_based_docs_expand_defs_symbols_before_rendering():
    path = ROOT / "fixtures" / "newset" / "faz-ai-manifesto-deck.v2.fg.yaml"
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
