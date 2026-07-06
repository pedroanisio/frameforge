#!/usr/bin/env python3
"""test_python_version_support.py — the ``>=3.10`` support claim must be HONEST.

``pyproject`` declares ``requires-python = ">=3.10"`` (codebase-standards §1) and
§16 row 8 commits to a 3.10–3.12 CI matrix + ``classifiers``. But ``tomllib`` is
stdlib only on **3.11+**, so any gate-running module that bare-imports it CRASHES
on the minimum Python the project claims to support — which ``test_docs_in_sync``
did, silently, until this row landed.

These tests pin the invariants that make the claim true:
  * every ``tomllib`` importer degrades to the ``tomli`` backport;
  * ``tomli`` is a declared dev dependency, marked ``python_version < "3.11"``, so
    the fallback actually resolves on 3.10 (it was only ever present transitively
    via pytest — an accident, not a contract); and
  * the ``classifiers`` name exactly the supported versions.
"""
import ast
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tooling"))

# Read pyproject via the SAME guarded idiom these tests enforce elsewhere.
try:
    import tomllib
except ModuleNotFoundError:  # Python 3.10 has no stdlib tomllib
    import tomli as tomllib  # type: ignore[no-redefine]


def _pyproject():
    with (ROOT / "pyproject.toml").open("rb") as fh:
        return tomllib.load(fh)


def _gate_py_files():
    for base in ("tests", "tooling"):
        for path in sorted((ROOT / base).rglob("*.py")):
            if "__pycache__" not in path.parts:
                yield path


def _top_level_imports(path):
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names |= {a.name.split(".")[0] for a in node.names}
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module.split(".")[0])
    return names


def test_no_unguarded_tomllib_under_py310_floor():
    """`tomllib` is 3.11+ stdlib; under requires-python >=3.10 every gate module
    that imports it must also import the `tomli` backport as its fallback, or it
    crashes on 3.10 — the defect that took test_docs_in_sync.py down."""
    offenders = []
    for path in _gate_py_files():
        imports = _top_level_imports(path)
        if "tomllib" in imports and "tomli" not in imports:
            offenders.append(str(path.relative_to(ROOT)))
    assert offenders == [], (
        "these modules import the 3.11+ stdlib `tomllib` without a `tomli` "
        f"fallback — they crash on the claimed-supported Python 3.10: {offenders}")


def test_tomli_backport_declared_for_py310():
    dev = _pyproject().get("dependency-groups", {}).get("dev", [])
    marked = [
        d for d in dev
        if isinstance(d, str) and re.match(r"^tomli\b", d)
        and "python_version" in d and "3.11" in d
    ]
    assert marked, (
        "the `tomli` TOML backport must be a declared dev dependency marked "
        "`python_version < \"3.11\"`, so the guarded tomllib fallback resolves on "
        f"3.10 instead of relying on pytest's transitive dep; dev group: {dev}")


def test_classifiers_declare_the_supported_pythons():
    proj = _pyproject().get("project", {})
    classifiers = proj.get("classifiers", [])
    for v in ("3.10", "3.11", "3.12"):
        assert any(f"Python :: {v}" in c for c in classifiers), (
            f"classifiers must name Python {v} (consistent with requires-python "
            f"{proj.get('requires-python')!r}); got {classifiers}")
    assert proj.get("requires-python") == ">=3.10", (
        "requires-python floor must stay 3.10 while the classifiers claim it")
