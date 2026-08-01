"""`to="html"` — the HTML target reachable through MCP, not just the CLI.

The MCP render pipeline could export `png` (the raster feedback loop) and `pdf`
(assemble the pages into a vector document). HTML was absent, so an agent that
wanted a shareable, self-contained, accessible page had no way to ask for one
without leaving the tool surface.

`html` joins as a third target with the same shape as `pdf`: the document is
written into the session directory and reported by path + URI + size, never
inlined — a whole HTML file would blow the MCP result budget on its own
(`FRAMEFORGE_MCP_MAX_RESULT_CHARS`). Unlike `pdf` it has no optional dependency,
so it can never report unavailable.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path[:0] = [ROOT, os.path.join(ROOT, "src")]

_shadow = sys.modules.get("frameforge")
if _shadow is not None and not hasattr(_shadow, "__path__"):
    del sys.modules["frameforge"]

DOC = {
    "dsl": "FrameForge", "version": "2.0.0", "title": "MCP HTML",
    "pages": [{
        "mode": "page", "id": "p1",
        "canvas": {"size": [400, 300], "units": "px"},
        "layers": [{"id": "main", "z": 0, "objects": [
            {"type": "rect", "id": "r", "box": [10, 10, 100, 50], "fill": "#3366cc"},
            {"type": "text", "id": "t", "box": [10, 80, 300, 24], "text": "hello"},
        ]}],
    }],
}


def _run(tmp_path, to="html", raster_png=False):
    from frameforge.mcp.pipeline import _validate_and_render_yaml
    return _validate_and_render_yaml(
        json.dumps(DOC),
        session_id="s1",
        session_dir=tmp_path,
        base_dir=tmp_path,
        max_pages=3,
        raster_png=raster_png,
        to=to,
    )


def _find(result, kind):
    for item in result.get("renders") or []:
        if item.get("kind") == kind:
            return item
    return None


def test_unknown_target_is_still_rejected_with_a_hint(tmp_path):
    result = _run(tmp_path, to="docx")
    assert result["ok"] is False
    assert "docx" in result["error"]
    assert "html" in result["hint"], "the hint must list the target that now exists"


def test_html_target_writes_a_document_into_the_session(tmp_path):
    result = _run(tmp_path)
    assert result.get("ok") is not False, result.get("error")
    entry = _find(result, "html")
    assert entry is not None, f"no html render entry: {result.get('renders')}"
    assert entry["mimeType"] == "text/html"
    assert Path(entry["path"]).exists()
    assert entry["uri"] == "frameforge://session/s1/document.html"
    assert entry["bytes"] > 0


def test_html_document_is_whole_and_paints_the_objects(tmp_path):
    result = _run(tmp_path)
    text = Path(_find(result, "html")["path"]).read_text(encoding="utf-8")
    assert text.startswith("<!DOCTYPE html>") and "</html>" in text
    assert 'id="r"' in text and 'id="t"' in text
    assert "hello" in text


def test_html_is_reported_by_reference_not_inlined(tmp_path):
    """The MCP result budget forbids returning a whole document inline."""
    result = _run(tmp_path)
    blob = json.dumps(result)
    assert "<!DOCTYPE html>" not in blob, "the HTML body was inlined into the result"
    summary = result.get("html")
    assert summary and summary["ok"] is True
    assert summary["path"] and summary["uri"] and summary["bytes"] > 0


def test_html_export_needs_no_optional_dependency(tmp_path):
    """Unlike `pdf`, this target can never report unavailable."""
    result = _run(tmp_path)
    assert result["html"]["ok"] is True
    assert "hint" not in result["html"]


def test_png_target_does_not_emit_html(tmp_path):
    result = _run(tmp_path, to="png")
    assert _find(result, "html") is None
    assert "html" not in result
