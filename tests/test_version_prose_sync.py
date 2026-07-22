#!/usr/bin/env python3
"""Version PROSE sites agree with `HEAD_VERSION` (the literal sites already do).

Drift-risk-map MODERATE #9: the version *literals* (pyproject / `__version__` /
schema `$id`) are contract-tested, but the *prose* restatements had no reader —
`model.py`'s `Document.version` field description said "HEAD is 2.3.0" two
minor versions after 2.5.0 shipped, and nothing read the CHANGELOG top block
or the spec front-matter. Pinned here (the model prose is now interpolated
from `HEAD_VERSION` so it cannot rot; these gates keep the hand-written sites
honest).
"""
from __future__ import annotations

import os
import re
import sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
_shadow = sys.modules.get("frameforge")
if _shadow is not None and not hasattr(_shadow, "__path__"):
    del sys.modules["frameforge"]
sys.path[:0] = [ROOT, os.path.join(ROOT, "src"), os.path.join(ROOT, "docs")]

from frameforge.model import Document, HEAD_VERSION  # noqa: E402


def test_document_version_field_prose_states_head_version():
    desc = Document.model_fields["version"].description or ""
    assert f"HEAD is {HEAD_VERSION}" in desc, (
        f"Document.version description says {desc!r}; expected it to state "
        f"'HEAD is {HEAD_VERSION}' (interpolate HEAD_VERSION, never hardcode)")


def test_model_source_interpolates_head_version_not_a_literal():
    src_path = os.path.join(ROOT, "src", "frameforge", "model.py")
    with open(src_path, encoding="utf-8") as fh:
        src = fh.read()
    assert "HEAD is {HEAD_VERSION}" in src, (
        "model.py hardcodes the HEAD version in prose again — use the "
        "f-string interpolation so bumps cannot leave it stale")


def test_changelog_top_block_states_head_version():
    with open(os.path.join(ROOT, "CHANGELOG.md"), encoding="utf-8") as fh:
        head = fh.read(600)
    m = re.search(r"\*\*Version:\*\*\s*`([^`]+)`", head)
    assert m, "CHANGELOG.md top block no longer states a **Version:** — keep it"
    assert m.group(1) == HEAD_VERSION, (
        f"CHANGELOG.md top block says {m.group(1)}; HEAD_VERSION is {HEAD_VERSION}")


def test_spec_frontmatter_states_head_version():
    spec = os.path.join(ROOT, "docs", "spec", "frameforge-v2-spec.md")
    with open(spec, encoding="utf-8") as fh:
        head = fh.read(800)
    m = re.search(r"^version:\s*(\S+)", head, re.M)
    assert m, "spec front-matter no longer carries a version: line"
    assert m.group(1) == HEAD_VERSION, (
        f"spec front-matter says {m.group(1)}; HEAD_VERSION is {HEAD_VERSION}")
