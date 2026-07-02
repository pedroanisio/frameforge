"""Per-session scratch-directory lifecycle, listing, cleanup, and resource reads."""
from __future__ import annotations

import base64
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlparse

from framegraph.mcp.config import SESSION_ID_RE
from framegraph.mcp.paths import _session_root
from framegraph.mcp.util import (
    _is_relative_to,
    _iso_from_timestamp,
    _page_svg_name,
    _positive_int,
)


def _session_id(session_id: str | None) -> str:
    sid = session_id or "session"
    if not SESSION_ID_RE.fullmatch(sid):
        raise ValueError("session_id must match [A-Za-z0-9][A-Za-z0-9_.-]{0,79}")
    return sid


def _prepare_session(root: Path, session_id: str) -> Path:
    session_dir = (root / session_id).resolve()
    if not _is_relative_to(session_dir, root):
        raise ValueError("session_id escapes the session root")
    session_dir.mkdir(parents=True, exist_ok=True)
    return session_dir


def _reset_session_outputs(session_dir: Path) -> None:
    """Remove a prior run's generated artifacts so a reused ``session_id`` re-renders fresh.

    The code-execution harness only (re)derives the document when ``OUTPUT_YAML_PATH``
    is absent (see :func:`_harness_source`), so a leftover ``generated.fg.yaml`` from an
    earlier run under the same ``session_id`` would be re-rendered in place of the edited
    document. Clearing the per-run outputs (the generated YAML and any page SVG/PNG
    renders) makes each invocation hermetic without forcing callers to rotate the id.
    """
    stale = [
        session_dir / "generated.fg.yaml",
        session_dir / "build_error.json",
        session_dir / "document.pdf",
        *session_dir.glob("page-*.svg"),
        *session_dir.glob("p*.png"),
    ]
    for path in stale:
        path.unlink(missing_ok=True)


def _prior_render_artifacts(session_dir: Path) -> list[str]:
    """Names of the rendered artifacts a fresh call in this session would replace.

    The per-call output reset (:func:`_reset_session_outputs`) makes each run
    hermetic but silently destroys a previous call's renders when a session id is
    shared across tools; callers snapshot this BEFORE producing so the replacement
    can be surfaced instead of discovered later (see the guide's clobber warning).
    """
    if not session_dir.is_dir():
        return []
    names = [path.name for path in session_dir.glob("p*.png")]
    names += [path.name for path in session_dir.glob("page-*.svg")]
    if (session_dir / "document.pdf").is_file():
        names.append("document.pdf")
    return sorted(names)


def _previous_session_tool(session_dir: Path) -> str | None:
    """The tool that produced this session's last diagnostics, if recorded."""
    path = session_dir / "diagnostics.json"
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    tool = data.get("tool") if isinstance(data, dict) else None
    return tool if isinstance(tool, str) and tool else None


def read_session_resource(uri: str, *, session_root: str | Path | None = None) -> dict[str, str]:
    """Read a ``framegraph://session/...`` artifact as an MCP resource payload."""
    root = _session_root(session_root)
    parsed = urlparse(uri)
    if parsed.scheme != "framegraph" or parsed.netloc != "session":
        raise ValueError("resource URI must start with framegraph://session/")
    parts = [unquote(part) for part in parsed.path.strip("/").split("/") if part]
    if len(parts) < 2:
        raise ValueError("resource URI is missing a session id and artifact path")
    sid = _session_id(parts[0])
    session_dir = (root / sid).resolve()
    if not _is_relative_to(session_dir, root.resolve()):
        raise ValueError("resource URI escapes the session root")

    artifact = parts[1:]
    if artifact == ["document.yaml"]:
        path = session_dir / "generated.fg.yaml"
        mime = "application/x-yaml"
    elif artifact == ["document.pdf"]:
        path = session_dir / "document.pdf"
        mime = "application/pdf"
    elif artifact == ["diagnostics.json"]:
        path = session_dir / "diagnostics.json"
        mime = "application/json"
    elif artifact == ["workspace.json"]:
        path = session_dir / "workspace.json"
        mime = "application/json"
    elif len(artifact) == 2 and artifact[0] == "page" and artifact[1].endswith(".svg"):
        page_number = artifact[1][:-4]
        path = session_dir / _page_svg_name(_positive_int(page_number, "page_number"))
        mime = "image/svg+xml"
    elif len(artifact) == 2 and artifact[0] == "page" and artifact[1].endswith(".png"):
        page_number = artifact[1][:-4]
        path = session_dir / f"p{_positive_int(page_number, 'page_number'):03d}.png"
        mime = "image/png"
    else:
        raise ValueError(f"unsupported resource artifact: {'/'.join(artifact)!r}")

    if not path.exists():
        available = (
            sorted(entry.name for entry in session_dir.iterdir() if entry.is_file())
            if session_dir.is_dir()
            else []
        )
        listing = ", ".join(available) if available else "none — the session has no artifacts yet"
        raise FileNotFoundError(
            f"{path} does not exist. Artifacts currently in session {sid!r}: {listing}. "
            "Every render tool resets its session's page-*.svg/p*.png on each call, so "
            "page/N.png holds the LAST call's render — re-render, or use a distinct session_id."
        )
    if mime in ("image/png", "application/pdf"):
        return {
            "uri": uri,
            "mimeType": mime,
            "blob": base64.b64encode(path.read_bytes()).decode("ascii"),
        }
    return {"uri": uri, "mimeType": mime, "text": path.read_text(encoding="utf-8")}


def list_sessions(*, session_root: str | Path | None = None) -> dict[str, Any]:
    """List per-session scratch directories under the session root with their size."""
    root = _session_root(session_root)
    sessions: list[dict[str, Any]] = []
    for entry in sorted(root.iterdir()):
        if not entry.is_dir() or not SESSION_ID_RE.fullmatch(entry.name):
            continue
        files = [path for path in entry.rglob("*") if path.is_file()]
        sessions.append(
            {
                "session_id": entry.name,
                "has_document": (entry / "generated.fg.yaml").exists(),
                "svg_pages": len(list(entry.glob("page-*.svg"))),
                "png_pages": len(list(entry.glob("p*.png"))),
                "bytes": sum(path.stat().st_size for path in files),
                "modified": _iso_from_timestamp(entry.stat().st_mtime),
                "document_uri": f"framegraph://session/{entry.name}/document.yaml",
            }
        )
    return {
        "ok": True,
        "session_root": str(root),
        "session_count": len(sessions),
        "sessions": sessions,
    }


def cleanup_sessions(
    *,
    session_root: str | Path | None = None,
    session_ids: list[str] | None = None,
    older_than_seconds: float | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Remove session scratch dirs by id or age. No criteria removes nothing (safe by default).

    Exactly one selector applies: ``session_ids`` removes those ids; otherwise
    ``older_than_seconds`` removes sessions whose directory mtime is older than the
    cutoff. ``dry_run`` reports the selection without deleting. The structured log
    lives as a file at the root and is never a deletion target.
    """
    root = _session_root(session_root)
    cutoff = None
    if session_ids is None and older_than_seconds is not None:
        cutoff = datetime.now(timezone.utc).timestamp() - float(older_than_seconds)

    selected: list[Path] = []
    for entry in sorted(root.iterdir()):
        if not entry.is_dir() or not SESSION_ID_RE.fullmatch(entry.name):
            continue
        if session_ids is not None:
            if entry.name in session_ids:
                selected.append(entry)
        elif cutoff is not None and entry.stat().st_mtime < cutoff:
            selected.append(entry)

    removed: list[str] = []
    for entry in selected:
        target = entry.resolve()
        if not _is_relative_to(target, root):  # defense in depth — never escape the root
            continue
        if not dry_run:
            shutil.rmtree(target, ignore_errors=True)
        removed.append(entry.name)
    return {
        "ok": True,
        "session_root": str(root),
        "dry_run": dry_run,
        "removed_count": len(removed),
        "removed": removed,
    }
