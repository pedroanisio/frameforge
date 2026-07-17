#!/usr/bin/env python3
"""The ``frameforge`` package must not import *up* into the ``tooling`` scripts.

This pins the rendering bounded-context boundary (codebase-standards §2/§13): an
installed ``frameforge`` wheel would not ship ``tooling/``, so any
``from tooling ...`` / ``import tooling`` inside ``frameforge/`` is an import-break
after install and the inverted dependency flagged as tension #1 in
``conceptual-analysis.md``. ``tooling/check_package_readiness.py`` asserts the same
thing as a hard *blocker*; this test pins it inside ``make check`` so it cannot
regress silently.
"""
from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PKG = ROOT / "src" / "frameforge"


def _imports_tooling(path: Path) -> bool:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if module == "tooling" or module.startswith("tooling."):
                return True
        elif isinstance(node, ast.Import):
            if any(a.name == "tooling" or a.name.startswith("tooling.") for a in node.names):
                return True
    return False


def test_frameforge_package_does_not_import_tooling():
    offenders = [
        str(path.relative_to(ROOT))
        for path in sorted(PKG.rglob("*.py"))
        if "__pycache__" not in path.parts and _imports_tooling(path)
    ]
    assert offenders == [], (
        "frameforge/ must not import the top-level 'tooling' package — it would not "
        f"ship in a wheel (codebase-standards §2/§13). Offenders: {offenders}"
    )
