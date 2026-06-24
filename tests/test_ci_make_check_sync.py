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
