#!/usr/bin/env python3
"""Check local public/open-source readiness guardrails.

This gate is intentionally local and deterministic. It does not decide whether a
remote repository should be made public; it checks that the tree itself has the
basic public-facing documents, intake templates, package metadata, and no obvious
tracked local artifacts or high-signal secret literals.
"""
from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TOOLING = Path(__file__).resolve().parent
if str(TOOLING) not in sys.path:
    sys.path.insert(0, str(TOOLING))

import check_package_readiness  # noqa: E402
import tracked_files  # noqa: E402

BLOCKER = "blocker"

REQUIRED_FILES = (
    "LICENSE",
    "README.md",
    "CONTRIBUTING.md",
    "SECURITY.md",
    "CODE_OF_CONDUCT.md",
    ".github/ISSUE_TEMPLATE/bug_report.yml",
    ".github/ISSUE_TEMPLATE/config.yml",
    ".github/ISSUE_TEMPLATE/feature_request.yml",
    ".github/pull_request_template.md",
)

FORBIDDEN_TRACKED_PARTS = {
    ".agent-tasks",
    ".venv",
    "dist",
    "node_modules",
    "out",
    "site",
}

SECRET_PATTERNS = {
    "private key": re.compile(r"-----BEGIN (?:RSA |OPENSSH |DSA |EC )?PRIVATE KEY-----"),
    "aws access key": re.compile(r"AKIA[0-9A-Z]{16}"),
    "github token": re.compile(r"(?:ghp|github_pat)_[A-Za-z0-9_]{20,}"),
    "openai key": re.compile(r"sk-[A-Za-z0-9]{20,}"),
    "slack token": re.compile(r"xox[baprs]-[A-Za-z0-9-]{20,}"),
}


@dataclass
class Finding:
    name: str
    ok: bool
    detail: str


def _git_ls_files() -> list[str]:
    return tracked_files.tracked_paths(ROOT)


def _check_required_files() -> Finding:
    missing = [path for path in REQUIRED_FILES if not (ROOT / path).is_file()]
    return Finding(
        "public governance and intake files present",
        ok=not missing,
        detail="all required files are present" if not missing else "missing: " + ", ".join(missing),
    )


def _check_package_ready() -> Finding:
    findings = check_package_readiness.evaluate()
    failed = [finding for finding in findings if not finding.ok]
    return Finding(
        "package readiness is strict-clean",
        ok=not failed,
        detail=("tooling/check_package_readiness.py reports no blockers or gaps"
                if not failed else "failed package checks: "
                + ", ".join(finding.name for finding in failed)),
    )


def _check_no_tracked_local_artifacts(files: list[str]) -> Finding:
    offenders = []
    for path in files:
        parts = set(Path(path).parts)
        if parts & FORBIDDEN_TRACKED_PARTS:
            offenders.append(path)
    return Finding(
        "no tracked local artifacts or vendored dependency directories",
        ok=not offenders,
        detail="tracked file set is clean" if not offenders else "tracked offenders: "
        + ", ".join(offenders[:12]),
    )


def _check_secret_literals(files: list[str]) -> Finding:
    offenders: list[str] = []
    for rel in files:
        path = ROOT / rel
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            # An index entry can be absent from the worktree (unstaged deletion,
            # sparse checkout) or unreadable (binary). Neither leaks a secret.
            continue
        for label, pattern in SECRET_PATTERNS.items():
            if pattern.search(text):
                offenders.append(f"{rel} ({label})")
    return Finding(
        "no high-signal secret literals in tracked text files",
        ok=not offenders,
        detail="no high-signal secret literals found" if not offenders else "possible secrets: "
        + ", ".join(offenders[:12]),
    )


def _check_issue_config_matches_enabled_features() -> Finding:
    name = ".github/ISSUE_TEMPLATE/config.yml"
    try:
        config = (ROOT / name).read_text(encoding="utf-8")
    except OSError as exc:
        return Finding(
            "issue-template contact links match enabled repository features",
            ok=False,
            detail=f"cannot read {name}: {exc.strerror}",
        )
    stale_links = []
    if "/discussions" in config:
        stale_links.append("GitHub Discussions link is present; enable Discussions first or remove the link")
    return Finding(
        "issue-template contact links match enabled repository features",
        ok=not stale_links,
        detail="no disabled-feature contact links found" if not stale_links else "; ".join(stale_links),
    )


def evaluate() -> list[Finding]:
    return [
        _check_required_files(),
        _check_package_ready(),
        # Index membership: a forbidden tracked path is an offender even while
        # its file is deleted locally.
        _check_no_tracked_local_artifacts(tracked_files.tracked_paths(ROOT)),
        # Readable content: nothing on disk means nothing to scan.
        _check_secret_literals(tracked_files.tracked_on_disk(ROOT)),
        _check_issue_config_matches_enabled_features(),
    ]


def main(argv: list[str] | None = None) -> int:
    argparse.ArgumentParser(
        description="Assert local public/open-source readiness guardrails."
    ).parse_args(argv)
    findings = evaluate()
    failures = [finding for finding in findings if not finding.ok]

    print("FrameForge — public readiness\n")
    for finding in findings:
        mark = "✓" if finding.ok else "✗"
        print(f"  {mark} {finding.name}")
        print(f"      {finding.detail}")

    print()
    if failures:
        print(f"NOT READY: {len(failures)} blocker(s).")
        return 1
    print("READY: local public-readiness guardrails pass.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
