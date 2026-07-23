#!/usr/bin/env python3
"""Offline relative-link checker for the documentation surface.

Fails if any tracked Markdown file contains a *relative* link whose target does
not exist on disk. External links (``http``/``https``/``mailto``), pure anchors
(``#section``), angle-bracket autolinks, and template placeholders are skipped,
as are links inside fenced code blocks.

Run *after* the generated MkDocs pages exist (``make docs``/``docs-check``): a
tracked doc may legitimately link to a generated page, which this resolves
against the on-disk tree. In ``make check`` this runs right after ``docs-check``.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TOOLING = Path(__file__).resolve().parent
if str(TOOLING) not in sys.path:
    sys.path.insert(0, str(TOOLING))

import tracked_files  # noqa: E402
# [text](target) and ![alt](src) — capture the target.
LINK_RE = re.compile(r"!?\[[^\]]*\]\(([^)]+)\)")


def tracked_md() -> list[Path]:
    """Tracked docs present in the worktree — a doc deleted locally has no links
    to resolve, and must not crash the gate."""
    return [ROOT / rel for rel in tracked_files.tracked_on_disk(ROOT, "*.md")]


def link_targets(path: Path):
    in_fence = False
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.lstrip()
        if stripped.startswith("```") or stripped.startswith("~~~"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        for m in LINK_RE.finditer(line):
            yield m.group(1).strip()


def main() -> int:
    files = tracked_md()
    broken: list[tuple[str, str]] = []
    for md in files:
        for raw in link_targets(md):
            target = raw.split()[0]  # drop an optional "title"
            if target.startswith(("http://", "https://", "mailto:", "#", "<")):
                continue
            if "{" in target:  # template placeholder, not a real path
                continue
            path_part = target.split("#", 1)[0]
            if not path_part:  # pure in-page anchor
                continue
            if path_part.startswith("/"):
                resolved = ROOT / path_part.lstrip("/")
            else:
                resolved = md.parent / path_part
            if not resolved.exists():
                broken.append((str(md.relative_to(ROOT)), raw))

    if broken:
        print(f"check_doc_links: {len(broken)} broken relative link(s):")
        for src, link in broken:
            print(f"  {src} -> {link}")
        return 1
    print(f"check_doc_links: OK — every relative link resolves ({len(files)} files).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
