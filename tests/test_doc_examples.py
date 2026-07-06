#!/usr/bin/env python3
"""
test_doc_examples.py — P3 executable documentation examples.

Every fenced ```yaml / ```json block in the prose that is a *complete* FrameGraph
document (carries the `dsl: FrameGraph` marker and has no `…` placeholders) is
parsed and validated against the models. A documentation example that drifts from
the schema fails CI — the prose can never show an invalid document.

Illustrative skeletons (blocks with `…`/`...` placeholders, e.g. the spec's
top-level shape) are intentionally skipped, not validated.

Sources scanned: the spec, docs/index.md, and README.md. Runs under pytest
(`uv run pytest`) or standalone (`uv run python tests/test_doc_examples.py`).
"""
import os
import re
import sys

import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))
sys.path[:0] = [os.path.join(ROOT, "docs", "models")]
# the top-level framegraph/ package would shadow models/framegraph.py
_shadow = sys.modules.get("framegraph")
if _shadow is not None and hasattr(_shadow, "__path__"):
    del sys.modules["framegraph"]

import framegraph as fg  # noqa: E402

SOURCES = ["docs/spec/framegraph-v2-spec.md", "docs/index.md", "README.md"]
_FENCE = re.compile(r"```(?:yaml|yml|json)\s*\n(.*?)\n```", re.S)
_DSL = re.compile(r'^\s*(?:dsl\s*:\s*["\']?FrameGraph\b|"dsl"\s*:\s*"FrameGraph")', re.M)


def _has_placeholder(block):
    return "…" in block or re.search(r'(?:^|\s)\.\.\.(?:\s|$)', block, re.M) is not None


def collect_examples():
    found = []
    for rel in SOURCES:
        path = os.path.join(ROOT, rel)
        if not os.path.exists(path):
            continue
        text = open(path, encoding="utf-8").read()
        for i, m in enumerate(_FENCE.finditer(text), 1):
            block = m.group(1)
            if _DSL.search(block) and not _has_placeholder(block):
                found.append((f"{rel}#{i}", block))
    return found


EXAMPLES = collect_examples()


def test_runnable_examples_present():
    assert EXAMPLES, "no complete FrameGraph examples found in the prose to validate"


try:
    import pytest

    @pytest.mark.parametrize("name,block", EXAMPLES, ids=[n for n, _ in EXAMPLES])
    def test_doc_example_validates(name, block):
        fg.Document.model_validate(yaml.safe_load(block))
except ImportError:  # pragma: no cover - pytest always present in the dev env
    pass


if __name__ == "__main__":
    if not EXAMPLES:
        print("FAIL: no runnable FrameGraph examples found in the prose")
        sys.exit(1)
    failed = 0
    for _name, _block in EXAMPLES:
        try:
            fg.Document.model_validate(yaml.safe_load(_block))
            print(f"  PASS  {_name}")
        except Exception as exc:  # noqa: BLE001
            print(f"  FAIL  {_name}: {str(exc).splitlines()[0]}")
            failed += 1
    print(f"\n{'OK' if not failed else 'FAILED'} ({len(EXAMPLES)} example(s), {failed} invalid)")
    sys.exit(1 if failed else 0)
