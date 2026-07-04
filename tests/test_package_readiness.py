#!/usr/bin/env python3
"""test_package_readiness.py — the package-emit checker must inspect the LIVE tree.

The 2026-07-02 folder refactor moved the importable package to ``src/framegraph``
and the model/schema reference sources under ``docs/``. ``check_package_readiness``
kept inspecting ``ROOT/framegraph``, ``ROOT/models``, ``ROOT/schema`` — paths that
no longer exist — so it silently:

  * dropped the real name-shadow blocker (``docs/models/framegraph.py`` still
    shadows the ``framegraph`` dist name, §2), and
  * reported the runtime ``__version__`` gap as still-open, although row 7 landed
    ``framegraph.__version__`` in ``src/framegraph/__init__.py`` (2026-07-04).

A verification tool that inspects a path that has moved passes *vacuously* — the
PALS's-Law failure mode (a broken verification layer is a design defect, not a
runtime bug). These tests pin the checker to the real layout and guard the paths
it inspects against going stale again.

Import note: the checker lives under ``tooling/`` and reads ``pyproject.toml``; it
does not touch the ``framegraph`` model shadow, so a plain ``tooling`` sys.path
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
    assert (CPR.SRC / "framegraph").is_dir(), (
        "checker must inspect the src-layout package src/framegraph")
    shadow_dirs = [ROOT / rel for rel in CPR.SHADOW_DIRS]
    assert any(d.is_dir() for d in shadow_dirs), (
        "at least one reference-source dir the checker scans for a name shadow "
        "must exist in the live tree")


# --------------------------------------------------------------------------- #
#  The verdict must be TRUE against the src-layout tree                        #
# --------------------------------------------------------------------------- #
def test_name_collision_detects_the_live_model_shadow():
    f = _by_name()["distribution name does not shadow a module"]
    assert not f.ok, (
        "docs/models/framegraph.py still shadows the `framegraph` dist name — a "
        "live blocker the checker must report, not drop")
    assert "docs/models/framegraph.py" in f.detail


def test_runtime_version_gap_is_closed_by_row_7():
    f = _by_name()["runtime __version__ exposed"]
    assert f.ok, (
        "row 7 landed framegraph.__version__ in src/framegraph/__init__.py; the "
        "checker must find it there and not report the gap as still open")


def test_verdict_matches_the_live_tree():
    """The standards §16 package-emit accounting quotes this verdict verbatim, so
    pin the exact live truth: three deliberate virtual-project blockers and two
    advisory gaps (the __version__ gap is closed by row 7)."""
    findings = CPR.evaluate()
    blockers = {f.name for f in findings if f.severity == CPR.BLOCKER and not f.ok}
    gaps = {f.name for f in findings if f.severity == CPR.GAP and not f.ok}
    assert blockers == {
        "build backend declared",
        "not a virtual project",
        "distribution name does not shadow a module",
    }, f"blockers drifted from the live tree: {blockers}"
    assert "runtime __version__ exposed" not in gaps, "row 7 closed the __version__ gap"
    assert gaps == {
        "py.typed marker shipped",
        "publish metadata polish",
    }, f"gaps drifted from the live tree: {gaps}"
