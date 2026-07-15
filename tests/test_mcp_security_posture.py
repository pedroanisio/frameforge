#!/usr/bin/env python3
"""MCP live security-posture discovery — ``security_posture()`` + capability wiring.

An agent (or operator) connecting to the server must be able to ask, at
runtime, what the effective confinement is: which propose-input roots apply
(``FRAMEGRAPH_MCP_INPUT_ROOTS``), which client roots are editable, and how SDK
code is executed (subprocess isolation, timeout, secret-env stripping). The
posture is computed PER CALL — flipping an env var must be reflected by the
next call in the same process — and is surfaced through
``describe_capabilities`` (index key + a dedicated ``security`` topic).
"""
from __future__ import annotations

import os
import sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
_shadow = sys.modules.get("framegraph")
if _shadow is not None and not hasattr(_shadow, "__path__"):
    del sys.modules["framegraph"]
sys.path[:0] = [ROOT, os.path.join(ROOT, "src"), os.path.join(ROOT, "docs")]

from framegraph.mcp.server import describe_capabilities  # noqa: E402

_POSTURE_ENV_VARS = (
    "FRAMEGRAPH_MCP_INPUT_ROOTS",
    "FRAMEGRAPH_MCP_KEEP_ENV",
    "FRAMEGRAPH_MCP_EDIT_ROOTS",
)


def _clear_posture_env(monkeypatch) -> None:
    for name in _POSTURE_ENV_VARS:
        monkeypatch.delenv(name, raising=False)


def _posture() -> dict:
    from framegraph.mcp.security import security_posture

    return security_posture()


def test_default_env_reports_open_mode_with_warnings(monkeypatch):
    _clear_posture_env(monkeypatch)

    posture = _posture()

    assert posture["input_roots"]["mode"] == "open"
    assert posture["input_roots"]["roots"] == []
    warnings = posture["warnings"]
    assert isinstance(warnings, list) and warnings, "open mode must warn"
    assert any("any readable path" in warning for warning in warnings)
    assert any("FRAMEGRAPH_MCP_INPUT_ROOTS" in warning for warning in warnings)


def test_default_edit_roots_cover_the_repo_client_root(monkeypatch):
    from framegraph.mcp.paths import get_default_repo_root

    _clear_posture_env(monkeypatch)

    posture = _posture()

    edit_roots = posture["edit_roots"]
    assert isinstance(edit_roots, list) and edit_roots
    assert all(isinstance(entry, str) and os.path.isabs(entry) for entry in edit_roots)
    expected = str((get_default_repo_root() / "static" / "examples").resolve())
    assert expected in edit_roots


def test_code_execution_posture_defaults(monkeypatch):
    _clear_posture_env(monkeypatch)

    execution = _posture()["code_execution"]

    assert execution["isolation"] == "subprocess"
    assert execution["sandboxed"] is False
    timeout = execution["timeout_seconds_default"]
    assert isinstance(timeout, int) and not isinstance(timeout, bool)
    assert timeout > 0
    assert execution["env_secret_stripping"] is True


def test_input_roots_env_switches_to_restricted_mode(tmp_path, monkeypatch):
    _clear_posture_env(monkeypatch)
    monkeypatch.setenv("FRAMEGRAPH_MCP_INPUT_ROOTS", str(tmp_path))

    posture = _posture()

    assert posture["input_roots"]["mode"] == "restricted"
    roots = posture["input_roots"]["roots"]
    assert str(tmp_path) in roots or str(tmp_path.resolve()) in roots
    assert not any("any readable path" in warning for warning in posture["warnings"])


def test_keep_env_disables_secret_stripping(monkeypatch):
    _clear_posture_env(monkeypatch)
    monkeypatch.setenv("FRAMEGRAPH_MCP_KEEP_ENV", "1")

    assert _posture()["code_execution"]["env_secret_stripping"] is False


def test_posture_is_computed_per_call(tmp_path, monkeypatch):
    _clear_posture_env(monkeypatch)

    first = _posture()
    assert first["input_roots"]["mode"] == "open"
    assert first["code_execution"]["env_secret_stripping"] is True

    monkeypatch.setenv("FRAMEGRAPH_MCP_INPUT_ROOTS", str(tmp_path))
    monkeypatch.setenv("FRAMEGRAPH_MCP_KEEP_ENV", "1")
    second = _posture()
    assert second["input_roots"]["mode"] == "restricted"
    assert second["code_execution"]["env_secret_stripping"] is False

    monkeypatch.delenv("FRAMEGRAPH_MCP_INPUT_ROOTS")
    monkeypatch.delenv("FRAMEGRAPH_MCP_KEEP_ENV")
    third = _posture()
    assert third["input_roots"]["mode"] == "open"
    assert third["code_execution"]["env_secret_stripping"] is True


def test_capability_index_carries_the_security_posture():
    result = describe_capabilities()

    assert result["ok"] is True
    assert "security" in result["topics"]
    posture = result["security_posture"]
    assert {"input_roots", "edit_roots", "code_execution", "warnings"} <= set(posture)
    assert posture["input_roots"]["mode"] in {"open", "restricted"}


def test_security_topic_returns_the_posture():
    result = describe_capabilities(topic="security")

    assert result["ok"] is True
    assert result["topic"] == "security"
    posture = result["security_posture"]
    assert {"input_roots", "edit_roots", "code_execution", "warnings"} <= set(posture)
    assert posture["code_execution"]["isolation"] == "subprocess"
