"""Session-root and repository-root resolution for the MCP server."""
from __future__ import annotations

import os
import tempfile
from pathlib import Path


def get_default_session_root() -> Path:
    """Return the default location for MCP session artifacts."""
    configured = os.environ.get("FRAMEGRAPH_MCP_SESSION_ROOT")
    if configured:
        return Path(configured).expanduser()
    return Path(tempfile.gettempdir()) / "framegraph-mcp-sessions"


def get_default_repo_root() -> Path:
    """Return the repository root that contains this MCP package (src layout:
    ``<root>/src/framegraph/mcp/paths.py``)."""
    return Path(__file__).resolve().parents[3]


def _session_root(session_root: str | Path | None) -> Path:
    root = Path(session_root) if session_root is not None else get_default_session_root()
    root = root.expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True)
    return root


def _repo_root(repo_root: str | Path | None) -> Path:
    return (Path(repo_root) if repo_root is not None else get_default_repo_root()).expanduser().resolve()
