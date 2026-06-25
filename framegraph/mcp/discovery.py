"""Content-hash discovery of the FrameGraph YAML a client run produced."""
from __future__ import annotations

import hashlib
from pathlib import Path

from framegraph.mcp.config import FRAMEGRAPH_YAML_PATTERNS


def _framegraph_yaml_snapshot(repo_root: Path) -> dict[Path, str]:
    """Content-hash snapshot of candidate fixtures before a client run.

    Hashes (not mtimes) so the post-run diff only fires on *content* change — a
    fixture merely ``touch``-ed by an unrelated process is no longer mistaken for
    this client's output, which the mtime heuristic could do.
    """
    return {
        path: hashlib.sha256(path.read_bytes()).hexdigest()
        for path in _framegraph_yaml_candidates(repo_root)
        if path.is_file()
    }


def _new_generated_yaml(repo_root: Path, before: dict[Path, str]) -> Path | None:
    changed: list[Path] = []
    for path in _framegraph_yaml_candidates(repo_root):
        if not path.is_file():
            continue
        previous = before.get(path)
        current = hashlib.sha256(path.read_bytes()).hexdigest()
        if previous is None or current != previous:
            changed.append(path)
    if not changed:
        return None
    # Tie-break by mtime when several fixtures changed in the same run.
    return max(changed, key=lambda candidate: candidate.stat().st_mtime_ns)


def _framegraph_yaml_candidates(repo_root: Path) -> list[Path]:
    candidates: list[Path] = []
    for root in (repo_root / "examples", repo_root / "fixtures"):
        if not root.exists():
            continue
        for pattern in FRAMEGRAPH_YAML_PATTERNS:
            candidates.extend(root.rglob(pattern))
    return candidates
