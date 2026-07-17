from __future__ import annotations

from pathlib import Path

from tooling import check_disclaimers


ROOT = Path(__file__).resolve().parent.parent
PUBLIC_GOVERNANCE_DOCS = {
    "CODE_OF_CONDUCT.md",
    "CONTRIBUTING.md",
    "LICENSE",
    "SECURITY.md",
}


def test_public_governance_docs_exist() -> None:
    missing = [path for path in PUBLIC_GOVERNANCE_DOCS if not (ROOT / path).is_file()]

    assert missing == []


def test_public_governance_docs_are_disclaimer_gate_exempt() -> None:
    governance_markdown = PUBLIC_GOVERNANCE_DOCS - {"LICENSE"}

    assert governance_markdown <= check_disclaimers.EXEMPT
