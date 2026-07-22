#!/usr/bin/env python3
"""Paths the CHANGELOG cites exist in the tree.

Drift-risk-map MODERATE #12: CHANGELOG claims are convention-only — entries
cite gate tests, ADRs, and modules as evidence, and nothing ever re-checks
that the cited artifact still exists. A renamed test or deleted doc leaves
the changelog asserting evidence that is not there. This gate resolves every
`tests/…`, `docs/…`, `src/…`, `tooling/…` path the CHANGELOG cites; paths
that were legitimately removed by later refactors belong in the explicit
HISTORICAL set (with the entry that removed them), not silently broken.
"""
from __future__ import annotations

import os
import re
import sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path[:0] = [ROOT, os.path.join(ROOT, "src"), os.path.join(ROOT, "docs")]

CHANGELOG = os.path.join(ROOT, "CHANGELOG.md")

# Paths later refactors removed/renamed on purpose — each with its remover.
HISTORICAL = {
    # the 2.5.0 packaging entry itself describes the move away from this path
    "docs/models/frameforge.py": "moved to src/frameforge/model.py by "
                                 "2.5.0 — feat(packaging)",
}

_PATH = re.compile(r"\b((?:tests|docs|src|tooling)/[A-Za-z0-9_\-./]+\.(?:py|md|json|ebnf|yaml|yml|mjs))\b")


def _cited():
    with open(CHANGELOG, encoding="utf-8") as fh:
        found = _PATH.findall(fh.read())
    # ignore prose ellipses ("src/frameforge/rendering/.../canvas_resolver.py")
    return sorted({p for p in found if "..." not in p})


def test_the_changelog_actually_cites_paths():
    assert len(_cited()) >= 10, "path regex found almost nothing — format changed?"


def test_every_cited_path_exists_or_is_historical():
    missing = [p for p in _cited()
               if p not in HISTORICAL and not os.path.exists(os.path.join(ROOT, p))]
    assert not missing, (
        "CHANGELOG.md cites path(s) that do not exist:\n  " + "\n  ".join(missing)
        + "\nEither fix the citation, or record the removal in HISTORICAL "
          "with the entry that removed it.")
