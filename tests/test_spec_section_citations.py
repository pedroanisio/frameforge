#!/usr/bin/env python3
"""Every `§x.y` the model's docstrings cite exists as a spec section.

Drift-risk-map MODERATE #11: `spec-check` pins discriminators, and dedicated
gates now pin reserved styles (§5.2.2) and preset dims (§4) — but the model's
field descriptions cite dozens of spec sections (`§9.3`, `§3.6e`, `§8.5`, …)
with no reader: renumber or drop a spec section and every citation silently
points at nothing (or worse, at the wrong rule). This gate parses every
section citation in `model.py` and asserts a matching numbered heading (or
explicit sub-item label) exists in the spec source.
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

MODEL = os.path.join(ROOT, "src", "frameforge", "model.py")
SPEC = os.path.join(ROOT, "docs", "spec", "frameforge-v2-spec.md")


def _cited():
    with open(MODEL, encoding="utf-8") as fh:
        src = fh.read()
    # §3, §3.6, §3.6e, §5.2.2 …
    return sorted(set(re.findall(r"§(\d+(?:\.\d+)*[a-z]?)", src)))


def _spec_sections():
    with open(SPEC, encoding="utf-8") as fh:
        spec = fh.read()
    nums = set()
    # numbered headings: "## 4. Canvas", "### 3.6 Containers", "#### 3.6e …",
    # and ranged headings: "### 3.1–3.2 Identity" cover every point inside.
    for m in re.finditer(r"^#{2,6}\s+(\d+(?:\.\d+)*[a-z]?)(?:[–-](\d+(?:\.\d+)*))?[.\s]",
                         spec, re.M):
        nums.add(m.group(1))
        if m.group(2):
            nums.add(m.group(2))
    # sub-item labels cited with letters ("§3.6e") are often bold list items
    # or inline anchors: "**3.6e**" / "(3.6e)" / "3.6e)" — collect those too.
    nums |= set(re.findall(r"[\s(*](\d+\.\d+[a-z])\)?[\s.,:*)]", spec))
    return nums


def _covered(cite, sections):
    if cite in sections:
        return True
    # "§3.6e" is covered by a "3.6" heading whose body defines the lettered
    # sub-items; "§5.2.2" by "5.2.2" or its parent "5.2" heading.
    if re.fullmatch(r"\d+(?:\.\d+)*[a-z]", cite) and cite.rstrip("abcdefghijklmnopqrstuvwxyz") in sections:
        return True
    parent = cite.rsplit(".", 1)[0]
    return "." in cite and parent in sections


def test_the_model_actually_cites_sections():
    assert len(_cited()) >= 10, "citation regex found almost nothing — format changed?"


def test_every_model_spec_citation_resolves():
    sections = _spec_sections()
    dead = [c for c in _cited() if not _covered(c, sections)]
    assert not dead, (
        f"model.py cites spec section(s) {dead} that no heading in "
        "docs/spec/frameforge-v2-spec.md provides — renumbered or removed "
        "sections leave citations pointing at nothing")
