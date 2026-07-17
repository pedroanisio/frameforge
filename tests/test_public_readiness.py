from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tooling"))

import check_public_readiness as CPR  # noqa: E402


def _by_name() -> dict[str, CPR.Finding]:
    return {finding.name: finding for finding in CPR.evaluate()}


def test_public_readiness_gate_passes_live_tree() -> None:
    findings = CPR.evaluate()
    failures = [finding for finding in findings if not finding.ok]

    assert failures == []


def test_public_readiness_checks_for_disabled_discussions_links() -> None:
    finding = _by_name()["issue-template contact links match enabled repository features"]

    assert finding.ok
    assert "Discussions" not in (ROOT / ".github/ISSUE_TEMPLATE/config.yml").read_text()
