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
PUBLIC_GITHUB_TEMPLATES = {
    ".github/ISSUE_TEMPLATE/bug_report.yml",
    ".github/ISSUE_TEMPLATE/config.yml",
    ".github/ISSUE_TEMPLATE/feature_request.yml",
    ".github/pull_request_template.md",
}


def test_public_governance_docs_exist() -> None:
    missing = [path for path in PUBLIC_GOVERNANCE_DOCS if not (ROOT / path).is_file()]

    assert missing == []


def test_public_governance_docs_are_disclaimer_gate_exempt() -> None:
    governance_markdown = PUBLIC_GOVERNANCE_DOCS - {"LICENSE"}

    assert governance_markdown <= check_disclaimers.EXEMPT


def test_public_github_intake_templates_exist() -> None:
    missing = [path for path in PUBLIC_GITHUB_TEMPLATES if not (ROOT / path).is_file()]

    assert missing == []


def test_public_github_intake_templates_route_security_privately() -> None:
    bug_template = (ROOT / ".github/ISSUE_TEMPLATE/bug_report.yml").read_text()
    config = (ROOT / ".github/ISSUE_TEMPLATE/config.yml").read_text()
    pr_template = (ROOT / ".github/pull_request_template.md").read_text()

    assert "SECURITY.md" in bug_template
    assert "security/advisories/new" in config
    assert "/discussions" not in config
    assert "No secrets" in pr_template
