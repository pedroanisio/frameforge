#!/usr/bin/env python3
"""MCP ``cleanup_sessions`` age-floor guardrail — contract tests (TDD RED).

A hard delete driven by ``older_than_seconds`` below a minimum-age floor is
almost always a mistake (``older_than_seconds=0`` wipes every session). The
contract under test:

* ``DEFAULT_MIN_CLEANUP_AGE_SECONDS = 60`` lives in ``framegraph.mcp.config``,
  overridable via ``FRAMEGRAPH_MCP_MIN_CLEANUP_AGE`` (the ``_positive_env``
  pattern) and read PER CALL, not at import time.
* A hard delete (``dry_run=False``) with ``older_than_seconds`` below the
  floor is refused structurally — ``{"ok": False, ...}`` with an ``error``
  naming the floor and a ``hint`` pointing at ``session_ids`` / ``dry_run`` —
  and deletes nothing.
* ``dry_run=True`` is exempt (a preview is harmless), the explicit
  ``session_ids`` selector is unaffected, and at/above-floor calls plus the
  no-selector no-op keep today's behavior.
"""
from __future__ import annotations

import os
import sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
_shadow = sys.modules.get("framegraph")
if _shadow is not None and not hasattr(_shadow, "__path__"):
    del sys.modules["framegraph"]
sys.path[:0] = [ROOT, os.path.join(ROOT, "src"), os.path.join(ROOT, "docs")]

import time  # noqa: E402
from pathlib import Path  # noqa: E402

from framegraph.mcp.sessions import cleanup_sessions  # noqa: E402


def _make_session(root: Path, name: str, *, age_seconds: float = 0.0) -> Path:
    """Create a session scratch dir; backdate its mtime AFTER writing contents."""
    session_dir = root / name
    session_dir.mkdir()
    (session_dir / "generated.fg.yaml").write_text("framegraph: '2.0'\n", encoding="utf-8")
    if age_seconds:
        stamp = time.time() - age_seconds
        os.utime(session_dir, (stamp, stamp))
    return session_dir


def test_min_cleanup_age_floor_constant_declared():
    # New symbol — imported lazily so only this test fails on the missing constant.
    from framegraph.mcp.config import DEFAULT_MIN_CLEANUP_AGE_SECONDS

    assert DEFAULT_MIN_CLEANUP_AGE_SECONDS == 60


def test_below_floor_hard_delete_is_refused_and_deletes_nothing(tmp_path, monkeypatch):
    monkeypatch.delenv("FRAMEGRAPH_MCP_MIN_CLEANUP_AGE", raising=False)
    _make_session(tmp_path, "session-a", age_seconds=3600)
    _make_session(tmp_path, "session-b", age_seconds=3600)

    result = cleanup_sessions(session_root=tmp_path, older_than_seconds=5)

    assert result["ok"] is False
    assert "60" in str(result["error"])  # the refusal names the effective floor
    assert "session_ids" in result["hint"]  # targeted removal escape hatch
    assert "dry_run" in result["hint"]  # preview escape hatch
    # Refusal means NOTHING was deleted, even though both dirs matched the cutoff.
    assert (tmp_path / "session-a").is_dir()
    assert (tmp_path / "session-b").is_dir()


def test_dry_run_is_exempt_from_the_floor(tmp_path, monkeypatch):
    monkeypatch.delenv("FRAMEGRAPH_MCP_MIN_CLEANUP_AGE", raising=False)
    _make_session(tmp_path, "session-a", age_seconds=10)
    _make_session(tmp_path, "session-b", age_seconds=10)

    result = cleanup_sessions(session_root=tmp_path, older_than_seconds=0, dry_run=True)

    assert result["ok"] is True
    assert result["dry_run"] is True
    assert set(result["removed"]) == {"session-a", "session-b"}
    assert (tmp_path / "session-a").is_dir()
    assert (tmp_path / "session-b").is_dir()


def test_explicit_session_ids_selector_is_unaffected_by_the_floor(tmp_path, monkeypatch):
    monkeypatch.delenv("FRAMEGRAPH_MCP_MIN_CLEANUP_AGE", raising=False)
    _make_session(tmp_path, "drop-me")
    _make_session(tmp_path, "keep-me")

    result = cleanup_sessions(session_root=tmp_path, session_ids=["drop-me"])

    assert result["ok"] is True
    assert result["removed"] == ["drop-me"]
    assert not (tmp_path / "drop-me").exists()
    assert (tmp_path / "keep-me").is_dir()


def test_at_or_above_floor_deletes_old_sessions_as_today(tmp_path, monkeypatch):
    monkeypatch.delenv("FRAMEGRAPH_MCP_MIN_CLEANUP_AGE", raising=False)
    _make_session(tmp_path, "old-one", age_seconds=3600)
    _make_session(tmp_path, "fresh-one")

    # Exactly at the floor (60) — the boundary is allowed, not refused.
    result = cleanup_sessions(session_root=tmp_path, older_than_seconds=60)

    assert result["ok"] is True
    assert result["removed"] == ["old-one"]
    assert not (tmp_path / "old-one").exists()
    assert (tmp_path / "fresh-one").is_dir()


def test_no_selector_still_removes_nothing(tmp_path, monkeypatch):
    monkeypatch.delenv("FRAMEGRAPH_MCP_MIN_CLEANUP_AGE", raising=False)
    _make_session(tmp_path, "session-a", age_seconds=3600)

    result = cleanup_sessions(session_root=tmp_path)

    assert result["ok"] is True
    assert result["removed_count"] == 0
    assert (tmp_path / "session-a").is_dir()


def test_env_override_lowers_the_floor_per_call_without_reimport(tmp_path, monkeypatch):
    """The floor must be read on every call: flipping the env var mid-process
    (no module reimport) changes the outcome of the very next call."""
    monkeypatch.delenv("FRAMEGRAPH_MCP_MIN_CLEANUP_AGE", raising=False)
    _make_session(tmp_path, "old-a", age_seconds=600)
    _make_session(tmp_path, "old-b", age_seconds=600)

    refused = cleanup_sessions(session_root=tmp_path, older_than_seconds=2)
    assert refused["ok"] is False
    assert (tmp_path / "old-a").is_dir()
    assert (tmp_path / "old-b").is_dir()

    monkeypatch.setenv("FRAMEGRAPH_MCP_MIN_CLEANUP_AGE", "1")
    done = cleanup_sessions(session_root=tmp_path, older_than_seconds=2)
    assert done["ok"] is True
    assert sorted(done["removed"]) == ["old-a", "old-b"]
    assert not (tmp_path / "old-a").exists()
    assert not (tmp_path / "old-b").exists()
