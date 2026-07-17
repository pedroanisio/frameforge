"""Regression coverage for newset documents that previously rendered with skips."""
from pathlib import Path

import yaml

from tooling.render_fixtures import Renderer


ROOT = Path(__file__).resolve().parent.parent
FIXTURES = [
    ROOT / "tests" / "fixtures" / "newset" / "code-base-mapper.deck.v2.fg.yaml",
    ROOT / "tests" / "fixtures" / "newset" / "frameforge_genai_mediated_system.v2.fg.yaml",
]


def test_newset_docs_render_without_silent_skips():
    for path in FIXTURES:
        doc = yaml.safe_load(path.read_text())
        renderer = Renderer(doc, str(path.parent))
        for page in doc.get("pages") or []:
            renderer.render_page(page)
        assert renderer.skipped == 0, f"{path.name} rendered with {renderer.skipped} skipped object(s)"
