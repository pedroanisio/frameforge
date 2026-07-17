#!/usr/bin/env python3
"""test_package_readiness.py — the package-emit checker must inspect the LIVE tree.

The 2026-07-02 folder refactor moved the importable package to ``src/frameforge``
and the model/schema reference sources under ``docs/``. ``check_package_readiness``
kept inspecting ``ROOT/frameforge``, ``ROOT/models``, ``ROOT/schema`` — paths that
no longer exist — so it silently:

  * dropped the real name-shadow blocker (``docs/models/frameforge.py`` still
    shadows the ``frameforge`` dist name, §2), and
  * reported the runtime ``__version__`` gap as still-open, although row 7 landed
    ``frameforge.__version__`` in ``src/frameforge/__init__.py`` (2026-07-04).

A verification tool that inspects a path that has moved passes *vacuously* — the
PALS's-Law failure mode (a broken verification layer is a design defect, not a
runtime bug). These tests pin the checker to the real layout and guard the paths
it inspects against going stale again.

Import note: the checker lives under ``tooling/`` and reads ``pyproject.toml``; it
does not touch the ``frameforge`` model shadow, so a plain ``tooling`` sys.path
insert is enough (no shadow-eviction dance — cf. test_grammar_sync.py).
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tooling"))

import check_package_readiness as CPR  # noqa: E402


def _by_name():
    return {f.name: f for f in CPR.evaluate()}


# --------------------------------------------------------------------------- #
#  Re-staleness guard — the checker must inspect paths that actually exist     #
# --------------------------------------------------------------------------- #
def test_checker_inspects_paths_that_actually_exist():
    """If the tree moves again, the checker must fail loudly rather than pass
    vacuously over a path that no longer exists. Every location it inspects is
    asserted present in the live tree."""
    assert (CPR.SRC / "frameforge").is_dir(), (
        "checker must inspect the src-layout package src/frameforge")
    shadow_dirs = [ROOT / rel for rel in CPR.SHADOW_DIRS]
    assert any(d.is_dir() for d in shadow_dirs), (
        "at least one reference-source dir the checker scans for a name shadow "
        "must exist in the live tree")


# --------------------------------------------------------------------------- #
#  The verdict must be TRUE against the src-layout tree                        #
# --------------------------------------------------------------------------- #
def test_name_collision_is_resolved_by_the_model_move():
    """2.5.0 moved the authoritative model into the package
    (src/frameforge/model.py); no module on a tooling sys.path root shares the
    distribution name any more, so an installed wheel shadows nothing."""
    f = _by_name()["distribution name does not shadow a module"]
    assert f.ok, (
        "a module named `frameforge` reappeared on a tooling sys.path root — "
        f"that reintroduces the shadow hazard 2.5.0 removed: {f.detail}")


def test_runtime_version_gap_is_closed_by_row_7():
    f = _by_name()["runtime __version__ exposed"]
    assert f.ok, (
        "row 7 landed frameforge.__version__ in src/frameforge/__init__.py; the "
        "checker must find it there and not report the gap as still open")


def test_verdict_matches_the_live_tree():
    """The standards §16 package-emit accounting quotes this verdict verbatim, so
    pin the exact live truth: as of 2.5.0 the tree is a real package — build
    backend declared, not virtual, no name shadow, py.typed shipped. Zero
    blockers, zero gaps: the checker must print READY."""
    findings = CPR.evaluate()
    blockers = {f.name for f in findings if f.severity == CPR.BLOCKER and not f.ok}
    gaps = {f.name for f in findings if f.severity == CPR.GAP and not f.ok}
    assert blockers == set(), f"packaging regressed — blockers reappeared: {blockers}"
    assert gaps == set(), f"packaging regressed — gaps reopened: {gaps}"


def test_sdist_excludes_local_runtime_artifacts():
    """The public source distribution must not publish local agent state,
    virtualenvs, build output, or vendored viewer dependencies."""
    f = _by_name()["source distribution excludes local artifacts"]

    assert f.ok, f.detail
    assert "/viewer/node_modules" in CPR.REQUIRED_SDIST_EXCLUDES
