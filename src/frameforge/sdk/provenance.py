"""In-memory authoring provenance that never enters a FrameForge document.

Builders use :class:`AuthoredDict` only while assembling plain mappings. Model
validation and serialization erase the subtype naturally; explicit raw-dict
paths call :func:`strip_provenance`. The MCP SDK subprocess enables capture by
default, while ordinary SDK callers pay no stack-walk cost unless requested.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

PROVENANCE_ENV = "FRAMEFORGE_SDK_PROVENANCE"
_FALSE_VALUES = {"", "0", "false", "no", "off"}


class AuthoredDict(dict):
    """A transient mapping carrying an author site and/or SDK helper name."""

    def __init__(
        self,
        value: dict[str, Any] | None = None,
        *,
        author_site: dict[str, Any] | None = None,
        helper: str | None = None,
    ) -> None:
        super().__init__(value or {})
        self.author_site = dict(author_site) if author_site else None
        self.helper = helper


def provenance_enabled(explicit: bool | None = None) -> bool:
    """Resolve an explicit capture flag or the MCP subprocess environment default."""
    if explicit is not None:
        return bool(explicit)
    # Keep the literal at the read site: tests/test_env_var_docs.py derives the
    # deployment-knob census from literal environment reads under ``src/``.
    return (
        os.environ.get("FRAMEFORGE_SDK_PROVENANCE", "").strip().lower()
        not in _FALSE_VALUES
    )


def capture_author_site() -> dict[str, Any] | None:
    """Return the first stack frame outside ``frameforge.sdk`` in O(stack depth)."""
    frame = sys._getframe(1)
    while frame is not None:
        filename = frame.f_code.co_filename
        normalized = filename.replace("\\", "/")
        if "/frameforge/sdk/" not in normalized:
            return {
                "file": Path(filename).name,
                "line": int(frame.f_lineno),
                "function": frame.f_code.co_name,
            }
        frame = frame.f_back
    return None


def with_author_site(value: dict[str, Any], site: dict[str, Any] | None) -> AuthoredDict:
    """Copy ``value`` into a transient mapping carrying ``site``."""
    helper = value.helper if isinstance(value, AuthoredDict) else None
    return AuthoredDict(value, author_site=site, helper=helper)


def mark_helper(value: dict[str, Any], helper: str) -> dict[str, Any]:
    """Mark a helper-produced mapping when MCP provenance capture is enabled."""
    if not provenance_enabled():
        return value
    site = value.author_site if isinstance(value, AuthoredDict) else None
    return AuthoredDict(value, author_site=site, helper=helper)


def clone_authored(value: AuthoredDict, items: dict[str, Any]) -> AuthoredDict:
    """Preserve transient annotations while recursively coercing mapping values."""
    return AuthoredDict(items, author_site=value.author_site, helper=value.helper)


def strip_provenance(value: Any) -> Any:
    """Recursively return ordinary containers with all transient metadata removed."""
    if isinstance(value, dict):
        return {key: strip_provenance(item) for key, item in value.items()}
    if isinstance(value, list):
        return [strip_provenance(item) for item in value]
    if isinstance(value, tuple):
        return tuple(strip_provenance(item) for item in value)
    return value


def provenance_map(value: Any) -> dict[str, dict[str, Any]]:
    """Return ``{JSON pointer prefix: author/helper site}`` for ``value``."""
    result: dict[str, dict[str, Any]] = {}

    def pointer(parts: tuple[str | int, ...]) -> str:
        if not parts:
            return ""
        escaped = [str(part).replace("~", "~0").replace("/", "~1") for part in parts]
        return "/" + "/".join(escaped)

    def walk(node: Any, path: tuple[str | int, ...], inherited: dict[str, Any] | None) -> None:
        site = inherited
        helper = None
        if isinstance(node, AuthoredDict):
            site = node.author_site or inherited
            helper = node.helper
            if site is not None and (node.author_site is not None or helper is not None):
                entry = dict(site)
                if helper:
                    entry["via"] = helper
                result[pointer(path)] = entry
        if isinstance(node, dict):
            for key, item in node.items():
                walk(item, (*path, str(key)), site)
        elif isinstance(node, (list, tuple)):
            for index, item in enumerate(node):
                walk(item, (*path, index), site)

    walk(value, (), None)
    return result


def format_author_site(site: dict[str, Any]) -> str:
    """Format a compact, non-absolute authoring locator for MCP results."""
    rendered = f"{site['file']}:{site['line']} in {site['function']}()"
    if site.get("via"):
        rendered += f" (via {site['via']})"
    return rendered


__all__ = [
    "AuthoredDict",
    "PROVENANCE_ENV",
    "capture_author_site",
    "clone_authored",
    "format_author_site",
    "mark_helper",
    "provenance_enabled",
    "provenance_map",
    "strip_provenance",
    "with_author_site",
]
