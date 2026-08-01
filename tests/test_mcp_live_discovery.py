#!/usr/bin/env python3
"""Regression coverage for MCP discovery freshness (GitHub #78)."""
from __future__ import annotations

import os
import pathlib
import shutil

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "src"), str(ROOT / "docs")]

from frameforge.mcp import live_discovery  # noqa: E402
from frameforge.mcp.server import create_server  # noqa: E402


class FakeFastMCP:
    def __init__(self, name: str, **kwargs):
        self.name = name
        self.kwargs = kwargs
        self.tools = {}
        self.resources = {}
        self.prompts = {}

    def tool(self, **_kwargs):
        def decorate(func):
            self.tools[func.__name__] = func
            return func

        return decorate

    def resource(self, uri: str, **_kwargs):
        def decorate(func):
            self.resources[uri] = func
            return func

        return decorate

    def prompt(self, **_kwargs):
        def decorate(func):
            self.prompts[func.__name__] = func
            return func

        return decorate


def _structured(result):
    return getattr(result, "structuredContent", result)


def _make_newest(path: Path, source_root: Path, addition: str) -> None:
    latest = max(candidate.stat().st_mtime_ns for candidate in source_root.rglob("*.py"))
    path.write_text(path.read_text(encoding="utf-8") + addition, encoding="utf-8")
    os.utime(path, ns=(path.stat().st_atime_ns, latest + 1_000_000))


def test_long_running_server_refreshes_sdk_and_guide_without_restart(tmp_path, monkeypatch):
    repo = tmp_path / "repo"
    source_root = repo / "src" / "frameforge"
    shutil.copytree(
        ROOT / "src" / "frameforge",
        source_root,
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
    )
    live_discovery._cached_request.cache_clear()
    server = create_server(
        session_root=tmp_path / "sessions",
        repo_root=repo,
        fastmcp_cls=FakeFastMCP,
    )

    initial = _structured(server.tools["describe_capabilities"](topic="sdk"))
    initial_names = {entry["name"] for entry in initial["exports"]}
    assert initial["introspected_at"].endswith("Z")
    assert initial["source_token"]
    assert "issue78_live_probe" not in initial_names

    # The SDK-export half of this probe retired with the 2026-08-01 split.
    #
    # It used to edit `source_root/sdk/__init__.py` — a COPY of the tree the
    # server watches — and assert a new export appeared without a restart. The
    # SDK is now the installed `frameforge-sdk` distribution, so its exports do
    # not come from that tree at all: the only way to make this assertion pass
    # again would be to mutate site-packages (an editable install points at the
    # developer's real checkout), which is not something a test may do.
    #
    # What still holds, and is still worth gating, is the mechanism itself: the
    # server must notice a source edit to a module it DOES own and refresh both
    # the guide and its source token without a restart. That is asserted below.
    # Live-reload of an installed dependency is the dependency's problem.

    initial_guide = server.tools["get_guide"]()
    assert "`source_token`" in initial_guide
    assert "`introspected_at`" in initial_guide
    marker = "Issue 78 live guide probe."
    guide_path = source_root / "mcp" / "guide.py"
    _make_newest(
        guide_path,
        source_root,
        f'\nFRAMEFORGE_GUIDE += "\\n\\n{marker}"\n',
    )
    refreshed_guide = server.tools["get_guide"]()
    assert marker not in initial_guide
    assert marker in refreshed_guide
    assert server.prompts["frameforge_guide"]() == refreshed_guide
    # The capability set is stable across an ENGINE edit — SDK exports come from
    # an installed distribution now — but the source token must still move,
    # because the server re-read the tree it owns.
    final_capabilities = _structured(server.tools["describe_capabilities"](topic="sdk"))
    assert {entry["name"] for entry in final_capabilities["exports"]} == initial_names
    assert final_capabilities["source_token"] != initial["source_token"]

    def unexpected_spawn(*_args, **_kwargs):
        raise AssertionError("same-token discovery must be served from the cache")

    monkeypatch.setattr(live_discovery.subprocess, "run", unexpected_spawn)
    assert _structured(server.tools["describe_capabilities"](topic="sdk")) == final_capabilities
    assert server.tools["get_guide"]() == refreshed_guide
