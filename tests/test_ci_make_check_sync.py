#!/usr/bin/env python3
"""
CI must delegate the Python gate to `make check`.

`Makefile` is the local source of truth for the full gate list. If CI hand-mirrors
the target dependencies, Makefile-only checks can silently stop blocking pull
requests. This regression keeps the workflow wired to the same entrypoint that
developers run locally.
"""
from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_ci_python_gate_runs_make_check():
    workflow = ROOT / ".github" / "workflows" / "ci.yml"
    text = workflow.read_text(encoding="utf-8")

    assert "run: make check" in text, (
        "CI must run `make check` directly so the workflow cannot drift from the "
        "Makefile's local gate list."
    )


def test_ci_python_gate_runs_the_multiversion_matrix():
    """§16 row 8: the python-gates job must run a matrix across the supported
    interpreters (3.10–3.12), so `requires-python = ">=3.10"` is exercised, not
    just asserted. Parsed structurally so a collapsed matrix fails loudly."""
    import yaml

    workflow = ROOT / ".github" / "workflows" / "ci.yml"
    cfg = yaml.safe_load(workflow.read_text(encoding="utf-8"))
    versions = cfg["jobs"]["python"]["strategy"]["matrix"]["python-version"]
    assert {str(v) for v in versions} >= {"3.10", "3.11", "3.12"}, (
        f"CI python matrix must cover 3.10/3.11/3.12; got {versions}")
