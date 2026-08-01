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
    # The viewer became a companion runtime; the SDK, the contract and the
    # vision lane became standalone packages. Every CHANGELOG entry citing one of
    # their old in-repo paths is a true statement about where that code lived.
    "tests/test_viewer_schema_contract.py": "removed with the bundled viewer",
    # The vision context became the standalone `frameforge-vision` package and
    # its unit tests went with it; the entries citing them are true statements
    # about where that code lived when they were written.
    "tests/test_gradient_fit_domain.py": "moved to frameforge-vision (2026-08-01)",
    # The render engine became the standalone `frameforge-render` package; this
    # module is now frameforge_render/application/audit.py. The entries citing
    # the old path are true statements about where that code lived.
    "src/frameforge/rendering/application/audit.py":
        "moved to frameforge-render (2026-08-01)",
    # The cookbook became the standalone `frameforge-example` distribution; its
    # generated index and the generator went with it. Every entry citing them is
    # a true statement about where that content lived when it was written.
    "docs/examples.md": "moved to frameforge-example (2026-08-01)",
    "tooling/gen_examples_index.py": "moved to frameforge-example (2026-08-01)",
    # Renamed the same day: the launcher's module name shadowed the new
    # `frameforge_render` distribution on sys.path (conftest puts tooling/ on
    # it) — the one-name-one-owner invariant conftest.py documents.
    "tooling/frameforge_render.py":
        "renamed to tooling/ff_render.py (2026-08-01) — the old name shadowed "
        "the frameforge_render distribution",
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
