#!/usr/bin/env python3
"""Assert whether this tree is ready to emit (build/publish) a Python package.

FrameForge became a *real package* in 2.5.0: the authoritative model moved into
the package (``src/frameforge/model.py``), the hatchling build backend landed,
and ``[tool.uv] package = true``. Until then the tree was deliberately a virtual
project (``package = false``, codebase-standards §2) because an installed
``frameforge`` distribution would have shadowed the model module at
``docs/models/frameforge.py``. This check keeps that end-state *measurable* —
every criterion that once blocked the build is now a regression gate, and it
exits non-zero if any of them reopens.

It changes nothing: it only inspects ``pyproject.toml``, the package tree, and the
import graph, then prints a verdict. Findings are split into **blockers** (a wheel
would fail to build or would import-break after install) and advisory **gaps** (the
§16 ``[Target]`` ledger — a publishable package wants them, but they don't break a
build). Default exit is non-zero if any blocker stands; ``--strict`` also fails on
gaps.

Usage::

    python tooling/check_package_readiness.py
    python tooling/check_package_readiness.py --strict
"""
from __future__ import annotations

import argparse
import re
from dataclasses import dataclass
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:  # Python 3.10 has no stdlib tomllib
    try:
        import tomli as tomllib  # type: ignore[no-redefine]
    except ModuleNotFoundError:  # pragma: no cover - dev envs ship 3.11+
        print("error: need Python 3.11+ (tomllib) or the `tomli` package to read pyproject.toml")
        raise SystemExit(2) from None

ROOT = Path(__file__).resolve().parent.parent

BLOCKER = "blocker"
GAP = "gap"

# The 2026-07-02 folder refactor moved the tree to a src layout: the importable
# package lives under src/, and the model/schema reference sources moved under
# docs/. This checker inspects those *live* locations. tests/test_package_readiness.py
# guards these paths against going stale again — a checker that inspects a path
# that has moved passes vacuously, the PALS's-Law failure mode.
SRC = ROOT / "src"                       # importable-package parent (src/frameforge)

# Reference-source dirs the tooling puts on sys.path (docs/models, docs/schema). A
# `<dist-name>.py` sitting in one of these is shadowed by an installed wheel of the
# same distribution — the documented docs/models/frameforge.py hazard (§2).
SHADOW_DIRS = ("docs/models", "docs/schema")

# Sibling top-level import roots that are NOT inside the distribution package and
# therefore would not ship in a `frameforge` wheel. Post-refactor `tooling` is the
# live risk (still a top-level package); `models`/`schema` are kept as defensive
# guards even though the reference sources moved under docs/.
SIBLING_ROOTS = ("models", "tooling", "schema")
_SIBLING_IMPORT = re.compile(
    r"^\s*(?:from|import)\s+(" + "|".join(SIBLING_ROOTS) + r")(?:[.\s,]|$)"
)


@dataclass
class Finding:
    """One package-readiness criterion and its verdict."""

    name: str
    ok: bool
    severity: str  # BLOCKER | GAP
    detail: str


def _load_pyproject() -> dict:
    with (ROOT / "pyproject.toml").open("rb") as fh:
        return tomllib.load(fh)


def _check_build_system(pp: dict) -> Finding:
    table = pp.get("build-system")
    backend = (table or {}).get("build-backend")
    return Finding(
        "build backend declared",
        ok=bool(backend),
        severity=BLOCKER,
        detail=(f"[build-system] build-backend = {backend!r}" if backend
                else "no [build-system] table — `uv build` / `python -m build` cannot build a wheel"),
    )


def _check_uv_package_flag(pp: dict) -> Finding:
    flag = pp.get("tool", {}).get("uv", {}).get("package")
    return Finding(
        "not a virtual project",
        ok=flag is not False,
        severity=BLOCKER,
        detail=("[tool.uv] package = false — the tree is a virtual project, declared "
                "un-buildable on purpose (codebase-standards §2)"
                if flag is False else "[tool.uv] package is not False"),
    )


def _check_name_collision(pp: dict) -> Finding:
    name = pp.get("project", {}).get("name", "")
    shadows = []
    # A module of the same name as the distribution, sitting on a sys.path root the
    # tooling uses, would be shadowed by the installed package (the documented
    # docs/models/frameforge.py hazard, §2).
    for rel in SHADOW_DIRS:
        candidate = ROOT / rel / f"{name}.py"
        if candidate.exists():
            shadows.append(f"{rel}/{name}.py")
    if (ROOT / f"{name}.py").exists():
        shadows.append(f"{name}.py")
    return Finding(
        "distribution name does not shadow a module",
        ok=not shadows,
        severity=BLOCKER,
        detail=(f"dist name {name!r} also exists as {', '.join(shadows)}; an installed "
                f"wheel would shadow it" if shadows
                else f"dist name {name!r} has no sibling-module collision"),
    )


def _check_package_self_contained(pp: dict) -> Finding:
    name = pp.get("project", {}).get("name", "")
    pkg = SRC / name
    leaks: list[str] = []
    if pkg.is_dir():
        for path in sorted(pkg.rglob("*.py")):
            if "__pycache__" in path.parts:
                continue
            for line in path.read_text(encoding="utf-8").splitlines():
                m = _SIBLING_IMPORT.match(line)
                if m:
                    rel = path.relative_to(ROOT).as_posix()
                    leaks.append(f"{rel} -> {m.group(1)}")
    # De-duplicate while preserving order.
    leaks = list(dict.fromkeys(leaks))
    return Finding(
        "package imports only itself + declared deps",
        ok=not leaks,
        severity=BLOCKER,
        detail=(f"{name}/ imports sibling roots that would not ship in the wheel "
                f"({len(leaks)} site(s)): " + "; ".join(leaks[:4])
                + (" …" if len(leaks) > 4 else "") if leaks
                else f"no imports of {'/'.join(SIBLING_ROOTS)} from {name}/"),
    )


def _check_core_metadata(pp: dict) -> Finding:
    proj = pp.get("project", {})
    required = ["name", "version", "description", "readme", "license", "requires-python"]
    missing = [k for k in required if not proj.get(k)]
    return Finding(
        "core project metadata present",
        ok=not missing,
        severity=BLOCKER,
        detail=("all present: " + ", ".join(required) if not missing
                else "missing [project] keys: " + ", ".join(missing)),
    )


def _check_runtime_version(pp: dict) -> Finding:
    name = pp.get("project", {}).get("name", "")
    init = SRC / name / "__init__.py"
    text = init.read_text(encoding="utf-8") if init.exists() else ""
    has = bool(re.search(r"^__version__\s*=", text, re.MULTILINE))
    return Finding(
        "runtime __version__ exposed",
        ok=has,
        severity=GAP,
        detail=(f"{name}/__init__.py defines __version__" if has
                else f"{name}/__init__.py has no __version__ (§9 [Target])"),
    )


def _check_py_typed(pp: dict) -> Finding:
    name = pp.get("project", {}).get("name", "")
    marker = SRC / name / "py.typed"
    return Finding(
        "py.typed marker shipped",
        ok=marker.exists(),
        severity=GAP,
        detail=(f"{name}/py.typed present" if marker.exists()
                else f"no {name}/py.typed — consumers get no inline types (§1 [Target])"),
    )


def _check_publish_metadata(pp: dict) -> Finding:
    proj = pp.get("project", {})
    nice = ["classifiers", "authors", "urls", "keywords"]
    missing = [k for k in nice if not proj.get(k)]
    return Finding(
        "publish metadata polish",
        ok=not missing,
        severity=GAP,
        detail=("present: " + ", ".join(nice) if not missing
                else "absent [project] keys: " + ", ".join(missing) + " (§1/§16 [Target])"),
    )


CHECKS = (
    _check_build_system,
    _check_uv_package_flag,
    _check_name_collision,
    _check_package_self_contained,
    _check_core_metadata,
    _check_runtime_version,
    _check_py_typed,
    _check_publish_metadata,
)


def evaluate() -> list[Finding]:
    pp = _load_pyproject()
    return [check(pp) for check in CHECKS]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Assert package-emit readiness for this tree.")
    ap.add_argument("--strict", action="store_true",
                    help="also fail on advisory gaps, not only hard blockers")
    args = ap.parse_args(argv)

    findings = evaluate()
    blockers = [f for f in findings if f.severity == BLOCKER and not f.ok]
    gaps = [f for f in findings if f.severity == GAP and not f.ok]

    print("FrameForge — package-emit readiness\n")
    for f in findings:
        mark = "✓" if f.ok else ("✗" if f.severity == BLOCKER else "•")
        tag = "" if f.ok else f"  [{f.severity}]"
        print(f"  {mark} {f.name}{tag}")
        print(f"      {f.detail}")

    ready = not blockers and (not gaps or not args.strict)
    print()
    if not blockers and not gaps:
        print("READY: this tree can emit a package.")
    elif not blockers:
        verdict = "NOT READY" if args.strict else "READY (with gaps)"
        print(f"{verdict}: 0 blockers, {len(gaps)} advisory gap(s).")
        print("  Gaps are the §16 [Target] ledger — they don't break a build.")
    else:
        print(f"NOT READY: {len(blockers)} blocker(s), {len(gaps)} gap(s).")
        print("  FrameForge has shipped as a real package since 2.5.0; a blocker")
        print("  here is a packaging REGRESSION, not the historical virtual stance.")
    return 0 if ready else 1


if __name__ == "__main__":
    raise SystemExit(main())
