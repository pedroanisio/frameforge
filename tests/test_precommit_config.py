#!/usr/bin/env python3
"""test_precommit_config.py — the pre-commit config must run the SAME gate as CI.

codebase-standards §10 / §16 row 6: `.pre-commit-config.yaml` is "the same gate,
earlier." The failure mode of a hand-authored hook list is drift — the config
mirrors a subset of gates that then diverges from `make check`. This test pins the
config to the same entrypoint developers and CI run (`make check`), the way
test_ci_make_check_sync pins the workflow, so the pre-commit hooks cannot silently
stop mirroring the Makefile's gate list.
"""
from __future__ import annotations

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / ".pre-commit-config.yaml"


def _hook_entries():
    cfg = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))
    entries = []
    for repo in cfg.get("repos", []):
        for hook in repo.get("hooks", []):
            entries.append(hook)
    return entries


def test_precommit_config_exists_and_parses():
    assert CONFIG.exists(), ".pre-commit-config.yaml must exist (§16 row 6)"
    cfg = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))
    assert isinstance(cfg.get("repos"), list) and cfg["repos"], (
        "the config must declare at least one repo of hooks")


def test_precommit_runs_make_check_so_it_cannot_drift():
    """A hook must run `make check` itself — the same gate CI runs — so the
    pre-commit surface cannot drift from the Makefile's gate list."""
    entries = [h.get("entry", "") for h in _hook_entries()]
    assert any("make check" in e for e in entries), (
        "a pre-commit hook must run `make check` (the full gate, drift-proof); "
        f"hook entries: {entries}")


def test_precommit_runs_the_fast_ruff_gate_at_commit_time():
    """The fast redefinition gate (F811) should run at commit time so a name
    collision is caught before it reaches a push/CI."""
    entries = [h.get("entry", "") for h in _hook_entries()]
    assert any("make ruff-check" in e for e in entries), (
        f"a pre-commit hook must run `make ruff-check`; hook entries: {entries}")
