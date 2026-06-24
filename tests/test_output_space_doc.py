#!/usr/bin/env python3
"""Protect docs/output-space.md against drift.

The output-space record is hand-written, so its conceptual prose cannot be
machine-verified. But its *concrete anchor* — the "Generated today" entry points
— is a manual mirror of the repo, exactly like the README "## Layout" map. This
gate asserts:

  * every repo path the doc cites in backticks actually exists (so a renamed or
    deleted backend turns the stale claim into a test failure, not a silent lie);
  * the README still cross-references the doc;
  * the doc still carries its disclaimer frontmatter (it is a design record).

Pure file checks — no model import. Runs under pytest or standalone
(`uv run python tests/test_output_space_doc.py`).
"""
import os
import re

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
DOC = os.path.join(ROOT, "docs", "output-space.md")

# A backtick-quoted token that looks like a repository file path.
_PATH_RE = re.compile(r"`([A-Za-z0-9_][A-Za-z0-9_./-]*\.(?:py|mjs|json|md|ebnf|ya?ml))`")


def _doc():
    return open(DOC, encoding="utf-8").read()


def test_cited_entry_points_exist():
    paths = sorted(set(_PATH_RE.findall(_doc())))
    assert paths, "output-space.md cites no entry-point paths to protect"
    missing = [p for p in paths if not os.path.exists(os.path.join(ROOT, p))]
    assert not missing, (
        f"output-space.md cites path(s) that no longer exist (DRIFT): {missing}. "
        "Update the doc's 'Generated today' anchor to match the repo.")


def test_readme_cross_references_the_doc():
    readme = open(os.path.join(ROOT, "README.md"), encoding="utf-8").read()
    assert "docs/output-space.md" in readme, \
        "README must cross-reference docs/output-space.md"


def test_doc_carries_disclaimer_frontmatter():
    doc = _doc()
    assert doc.startswith("---\n"), "output-space.md must open with YAML frontmatter"
    front = doc.split("---", 2)[1]
    assert "disclaimer:" in front and "date:" in front


if __name__ == "__main__":
    test_cited_entry_points_exist()
    test_readme_cross_references_the_doc()
    test_doc_carries_disclaimer_frontmatter()
    print("output-space.md: anchor paths exist, README cross-refs it, frontmatter present")
