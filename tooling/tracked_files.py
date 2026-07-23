#!/usr/bin/env python3
"""The shared tracked-file enumerator for the gates and generators.

``git ls-files`` reports the **index**. The gates read the **worktree**. Those
two views diverge routinely — an unstaged deletion, a sparse or partial
checkout, a concurrent session mid-edit — and a caller that feeds an index entry
straight to ``open()`` turns that ordinary divergence into a traceback instead
of a finding.

Three questions, three functions. Pick by what the caller actually asks:

``tracked_paths``
    *Is this path tracked?* Index membership; worktree presence is not implied.
    The right list for path-shape rules, which must still flag a forbidden
    tracked path whose file happens to be deleted locally.

``tracked_on_disk``
    *Which tracked files can I read?* Mandatory for any checker that opens the
    file. A file absent from the worktree has no content to violate a rule, so
    skipping it is the correct answer rather than a suppressed error.

``read_tracked``
    *What does the tracked file say?* Worktree copy when present, indexed blob
    otherwise. For generators, whose committed output is gated against the
    index: a local deletion must not silently drop a row.
"""
from __future__ import annotations

import subprocess
from pathlib import Path


def tracked_paths(root: Path | str, *patterns: str) -> list[str]:
    """Repo-relative paths tracked in ``root``'s git index, sorted.

    Returns ``[]`` when git is unavailable or ``root`` is not a repository, so
    callers degrade to their own discovery instead of crashing. ``-z`` keeps
    paths with spaces or non-ASCII bytes intact (git quotes them otherwise).
    """
    try:
        proc = subprocess.run(
            ["git", "ls-files", "-z", *patterns],
            cwd=str(root),
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:
        return []
    if proc.returncode != 0:
        return []
    return sorted(entry for entry in proc.stdout.split("\0") if entry)


def tracked_on_disk(root: Path | str, *patterns: str) -> list[str]:
    """``tracked_paths`` filtered to entries that exist in the worktree."""
    base = Path(root)
    return [rel for rel in tracked_paths(base, *patterns) if (base / rel).is_file()]


def missing_from_worktree(root: Path | str, *patterns: str) -> list[str]:
    """Tracked paths whose file is absent from the worktree (deleted, unstaged)."""
    base = Path(root)
    return [rel for rel in tracked_paths(base, *patterns) if not (base / rel).is_file()]


def read_tracked(root: Path | str, rel: str, *, encoding: str = "utf-8") -> str | None:
    """Text of a tracked file: the worktree copy, else the indexed blob.

    ``None`` when neither is readable. Keeps generator output faithful to the
    index while a file is transiently deleted from the worktree.
    """
    base = Path(root)
    path = base / rel
    if path.is_file():
        try:
            return path.read_text(encoding=encoding)
        except (OSError, UnicodeDecodeError):
            return None
    try:
        proc = subprocess.run(
            ["git", "show", f":{rel}"],
            cwd=str(base),
            capture_output=True,
            text=True,
            encoding=encoding,
            check=False,
        )
    except (OSError, UnicodeDecodeError):
        return None
    return proc.stdout if proc.returncode == 0 else None
