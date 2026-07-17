"""sdk.from_markdown — document-level Markdown → a v2 flow document.

Closes absorption issue #31. Frameforge lowered *inline* Markdown only
(`sdk.macros.md`); this converts whole CommonMark/GFM-subset documents into a
validated `mode: flow` page, reusing the existing inline lowering — one inline
parser, not two. The ```` ```frameforge ```` pattern-directive degrades to a
structured warning until #29 lands.

Every conversion in this file round-trips through the authoritative model
(`validate_document`) — PALS's Law: converter output is untrusted until the
schema has said otherwise.

Runs under pytest or standalone (``uv run python tests/test_sdk_markdown.py``).
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "docs")]

from frameforge.sdk import from_markdown  # noqa: E402
from frameforge.sdk.model import validate_document  # noqa: E402


def _story(doc):
    assert doc["pages"][0]["mode"] == "flow"
    return doc["pages"][0]["story"]


def _kinds(story):
    return [fl["type"] for fl in story]


def _convert(md, **kw):
    doc = from_markdown(md, **kw)
    validate_document(doc)          # every conversion must be schema-legal
    return doc


# ── blocks ────────────────────────────────────────────────────────────────


def test_headings_paragraphs_and_rule():
    doc = _convert("# Title\n\nSome prose.\n\n## Section\n\nMore prose.\n\n---\n\nAfter the break.\n")
    story = _story(doc)
    assert _kinds(story) == ["heading", "paragraph", "heading", "paragraph",
                             "page_break", "paragraph"]
    assert story[0]["level"] == 1 and story[0]["text"] == "Title"
    assert story[2]["level"] == 2


def test_inline_markdown_delegates_to_the_existing_lowering():
    doc = _convert("Strong **bold** and `code` here.\n")
    para = _story(doc)[0]
    # md() lowering produces span runs when inline forms appear
    assert isinstance(para.get("spans"), list)
    flattened = "".join(s.get("text", "") if isinstance(s, dict) else str(s)
                        for s in para["spans"])
    assert "bold" in flattened and "code" in flattened


def test_lists_nested_and_ordered():
    doc = _convert("- one\n- two\n  - two.a\n  - two.b\n- three\n\n1. first\n2. second\n")
    story = _story(doc)
    assert _kinds(story) == ["list", "list"]
    outer = story[0]
    assert outer.get("ordered") in (None, False)
    # the model has no nested list: sub-items fold into their parent item as
    # marked continuation lines (documented limitation)
    assert len(outer["items"]) == 3
    second = outer["items"][1]
    second_text = second if isinstance(second, str) else second.get("text", "")
    assert "two.a" in second_text and "two.b" in second_text
    assert story[1]["ordered"] is True
    assert len(story[1]["items"]) == 2


def test_gfm_table():
    doc = _convert("| a | b |\n|---|---|\n| 1 | 2 |\n| 3 | 4 |\n")
    table = _story(doc)[0]
    assert table["type"] == "table"
    assert len(table["rows"]) == 2


def test_fenced_code_block():
    doc = _convert("```python\nprint('hi')\n```\n")
    code = _story(doc)[0]
    assert code["type"] == "code"
    assert code["language"] == "python"
    assert "print" in code["source"]


def test_blockquote_becomes_a_role_tagged_block():
    doc = _convert("> quoted wisdom\n> continues here\n")
    block = _story(doc)[0]
    assert block["type"] == "block" and block["role"] == "blockquote"
    assert block["children"][0]["type"] == "paragraph"


def test_image_becomes_image_flowable():
    doc = _convert("![a diagram](figs/arch.png)\n")
    img = _story(doc)[0]
    assert img["type"] == "image" and img["src"] == "figs/arch.png"
    assert img["alt"] == "a diagram"


# ── front-matter, directives, options ────────────────────────────────────


def test_front_matter_sets_document_identity():
    doc = _convert("---\ntitle: My Doc\nlang: en\n---\n\n# H\n\nBody.\n")
    assert doc["title"] == "My Doc" and doc["lang"] == "en"


def test_frameforge_directive_degrades_to_a_warning():
    sink: list = []
    doc = from_markdown("# T\n\n```frameforge\nuse: 44\nfill: {}\n```\n\nAfter.\n",
                        warnings=sink)
    validate_document(doc)
    assert sink and "frameforge" in sink[0] and "#29" in sink[0]
    # the directive itself emits nothing; surrounding content survives
    assert _kinds(_story(doc)) == ["heading", "paragraph"]


def test_title_falls_back_to_first_h1():
    doc = _convert("# The Letter\n\nBody.\n")
    assert doc["title"] == "The Letter"


# ── CLI front door accepts .md ───────────────────────────────────────────


def test_cli_renders_markdown_input(tmp_path):
    import os
    import subprocess
    md = tmp_path / "doc.md"
    md.write_text("# Hello\n\nA paragraph of body text.\n", encoding="utf-8")
    out = tmp_path / "out"
    env = dict(os.environ)
    env["PYTHONPATH"] = os.pathsep.join([str(ROOT / "src"), str(ROOT / "docs")])
    proc = subprocess.run(
        [sys.executable, "-m", "frameforge.cli", str(md), "--to", "svg",
         "--out", str(out)],
        capture_output=True, text=True, env=env, cwd=ROOT)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    svgs = list(out.glob("*.svg"))
    assert svgs and "Hello" in svgs[0].read_text(encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
