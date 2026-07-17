#!/usr/bin/env python3
"""Fail if an AI-authored Markdown doc is missing the rule-5 disclaimer frontmatter.

CLAUDE.md (Behavioral Constraints, rule 5) requires every AI-agent-authored
Markdown document to carry a ``disclaimer:`` YAML frontmatter block. This gate
asserts it for every tracked ``*.md`` except the explicitly exempt set:

- READMEs — navigation/usage front-doors (any ``README.md``).
- Governance / human front-door docs — ``CHANGELOG.md``, ``CLAUDE.md``,
  ``CONTRIBUTING.md``, ``SECURITY.md``, ``CODE_OF_CONDUCT.md``.
- Generated docs whose frontmatter is the generator's responsibility —
  ``docs/sdk.md``, ``docs/sdk-api.md``, ``docs/FIXTURE-STATUS.md``,
  ``fixtures/corpus/PROVENANCE.md``.

To exempt a new file, add it to ``EXEMPT`` (with a reason) rather than weakening
the check.
"""
from __future__ import annotations

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

EXEMPT = {
    "CHANGELOG.md",                     # release log (governance)
    "CLAUDE.md",                        # agent operating guide (governance)
    "CODE_OF_CONDUCT.md",               # public governance front-door
    "CONTRIBUTING.md",                  # public governance front-door
    "SECURITY.md",                      # public vulnerability-reporting policy
    "docs/sdk.md",                      # generated SDK snapshot
    "docs/sdk-api.md",                  # generated SDK snapshot
    "docs/FIXTURE-STATUS.md",                # generated from the validator
    "tests/fixtures/corpus/PROVENANCE.md",    # generated (do-not-hand-edit)
}


def tracked_md() -> list[str]:
    out = subprocess.run(
        ["git", "ls-files", "*.md"], cwd=ROOT, capture_output=True, text=True
    ).stdout
    return [p for p in out.split() if p]


def has_disclaimer(path: Path) -> bool:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---"):
        return False
    end = text.find("\n---", 3)
    frontmatter = text[:end] if end != -1 else text[:600]
    return "disclaimer:" in frontmatter


def main() -> int:
    missing = []
    for rel in tracked_md():
        if rel in EXEMPT or Path(rel).name == "README.md":
            continue
        if not has_disclaimer(ROOT / rel):
            missing.append(rel)
    if missing:
        print(f"check_disclaimers: {len(missing)} doc(s) missing the rule-5 "
              "disclaimer frontmatter:")
        for m in missing:
            print(f"  {m}")
        print("  Add the `disclaimer:` block (CLAUDE.md rule 5), or add the file "
              "to EXEMPT in tooling/check_disclaimers.py with a reason.")
        return 1
    print("check_disclaimers: OK — every non-exempt tracked doc carries the "
          "disclaimer frontmatter.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
