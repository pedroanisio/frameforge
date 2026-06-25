"""Path-traversal confinement for editable client files and propose inputs."""
from __future__ import annotations

import os
from pathlib import Path

from framegraph.mcp.config import DEFAULT_CLIENT_ROOTS
from framegraph.mcp.util import _is_relative_to


def _client_roots(repo_root: Path, edit_roots: str | list[str] | tuple[str, ...] | None) -> list[Path]:
    configured = edit_roots
    if configured is None:
        configured = os.environ.get("FRAMEGRAPH_MCP_EDIT_ROOTS")
    if configured is None:
        entries: list[str] = list(DEFAULT_CLIENT_ROOTS)
    elif isinstance(configured, str):
        entries = [entry for entry in configured.split(os.pathsep) if entry]
    else:
        entries = list(configured)

    roots: list[Path] = []
    for entry in entries:
        candidate = Path(entry).expanduser()
        if candidate.is_absolute():
            resolved = candidate.resolve()
            if not _is_relative_to(resolved, repo_root):
                as_repo_relative = (repo_root / str(entry).lstrip("/")).resolve()
                resolved = as_repo_relative
        else:
            resolved = (repo_root / candidate).resolve()
        if not _is_relative_to(resolved, repo_root):
            raise ValueError("editable SDK client roots must stay inside the repository")
        roots.append(resolved)
    if not roots:
        raise ValueError("at least one editable SDK client root is required")
    return roots


def _resolve_client_path(
    path: str,
    *,
    repo_root: Path,
    edit_roots: str | list[str] | tuple[str, ...] | None,
    must_exist: bool,
) -> Path:
    if not isinstance(path, str) or not path.strip():
        raise ValueError("path must be a non-empty string")
    raw = Path(path).expanduser()
    if raw.is_absolute():
        resolved = raw.resolve()
        if not _is_relative_to(resolved, repo_root):
            resolved = (repo_root / str(path).lstrip("/")).resolve()
    else:
        resolved = (repo_root / raw).resolve()
    if resolved.suffix != ".py":
        raise ValueError("SDK client path must be a Python .py file")
    allowed_roots = _client_roots(repo_root, edit_roots)
    if not any(_is_relative_to(resolved, root) for root in allowed_roots):
        raise ValueError("SDK client path must stay under the allowed SDK client roots")
    if must_exist and not resolved.is_file():
        raise FileNotFoundError(str(resolved))
    return resolved


def _repo_relative_path(path: Path, repo_root: Path) -> str:
    return path.resolve().relative_to(repo_root).as_posix()


def _assert_input_path_allowed(path: str) -> None:
    """Confine propose inputs to ``FRAMEGRAPH_MCP_INPUT_ROOTS`` when it is set.

    Unset (the default) preserves the open localhost-dev behavior: any readable
    path is accepted. Setting the env var to a ``os.pathsep``-joined list of roots
    locks the propose tools to those directories so the server cannot be used as a
    confused-deputy file reader in a hardened deployment.
    """
    configured = os.environ.get("FRAMEGRAPH_MCP_INPUT_ROOTS")
    if not configured:
        return
    roots = [Path(entry).expanduser().resolve() for entry in configured.split(os.pathsep) if entry]
    if not roots:
        return
    resolved = Path(path).expanduser().resolve()
    if not any(_is_relative_to(resolved, root) for root in roots):
        raise ValueError("input path is outside the allowed FRAMEGRAPH_MCP_INPUT_ROOTS")
