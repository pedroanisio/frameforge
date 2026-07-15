#!/usr/bin/env python3
"""MCP structured-log secret redaction — contract tests (TDD RED).

The JSONL structured log written by ``_logged_call`` / ``_append_structured_log``
records every tool instruction and response verbatim, so a secret literal inside
submitted SDK code (``API_KEY = "..."``, ``token: "..."``, ``password='...'``,
``Authorization: Bearer ...``) lands on disk in cleartext. Contract under test:

* Secret-looking KEY-VALUE literals inside logged string fields are redacted —
  the VALUE becomes ``[REDACTED]``, the key name stays visible — in both the
  instruction and the response, including the exception path.
* Prose and plain styling values (``fill = "red"``, ``Token of appreciation``,
  ``#ff0000``) are NOT redacted (false-positive guard).
* Redaction applies only to the on-disk log copy: the caller still receives the
  raw, unmodified response.
* The existing 20K-char field truncation still applies alongside redaction.
"""
from __future__ import annotations

import os
import sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
_shadow = sys.modules.get("framegraph")
if _shadow is not None and not hasattr(_shadow, "__path__"):
    del sys.modules["framegraph"]
sys.path[:0] = [ROOT, os.path.join(ROOT, "src"), os.path.join(ROOT, "docs")]

import json  # noqa: E402
from pathlib import Path  # noqa: E402

import pytest  # noqa: E402

from framegraph.mcp.config import STRUCTURED_LOG_MAX_FIELD_CHARS  # noqa: E402
from framegraph.mcp.logging import _logged_call  # noqa: E402


def _last_log_line(log_path: Path) -> str:
    lines = [line for line in log_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert lines, "structured log has no entries"
    return lines[-1]


MUST_REDACT_CASES = [
    pytest.param(
        "code",
        'API_KEY = "sk-live-abc123def456"\nprint("hello")\n',
        "sk-live-abc123def456",
        "API_KEY",
        id="python-assignment-api-key",
    ),
    pytest.param(
        "yaml_text",
        'title: demo\ntoken: "ghp_abcdef1234567890"\n',
        "ghp_abcdef1234567890",
        "token",
        id="yaml-token",
    ),
    pytest.param(
        "code",
        "password='hunter2secret'",
        "hunter2secret",
        "password",
        id="single-quoted-password",
    ),
    pytest.param(
        "code",
        'headers = "Authorization: Bearer eyJabc.def.ghi"',
        "eyJabc.def.ghi",
        "Authorization",
        id="authorization-bearer",
    ),
]


@pytest.mark.parametrize("field,text,secret,key_name", MUST_REDACT_CASES)
def test_instruction_secret_values_are_redacted_in_the_log(tmp_path, field, text, secret, key_name):
    log_path = tmp_path / "mcp-structured-log.jsonl"

    _logged_call(log_path, "run_sdk_code", {field: text}, lambda: {"ok": True})

    line = _last_log_line(log_path)
    assert secret not in line  # the secret VALUE never reaches disk
    assert "[REDACTED]" in line
    assert key_name in line  # the key name stays visible for debugging


def test_response_secret_values_are_redacted_in_log_but_caller_gets_raw(tmp_path):
    log_path = tmp_path / "mcp-structured-log.jsonl"
    secret_yaml = 'token: "ghp_abcdef1234567890"'
    response = {"ok": True, "generated_yaml": secret_yaml}

    result = _logged_call(log_path, "run_sdk_code", {"code": "print('hi')"}, lambda: response)

    # Redaction applies ONLY to the on-disk log copy; the caller is unaffected.
    assert result["generated_yaml"] == secret_yaml
    line = _last_log_line(log_path)
    assert "ghp_abcdef1234567890" not in line
    assert "[REDACTED]" in line


def test_exception_path_redacts_logged_string_fields(tmp_path):
    log_path = tmp_path / "mcp-structured-log.jsonl"

    def boom():
        raise ValueError("build failed near password='hunter2secret'")

    with pytest.raises(ValueError):
        _logged_call(
            log_path, "run_sdk_code", {"code": 'API_KEY = "sk-live-abc123def456"'}, boom
        )

    line = _last_log_line(log_path)
    assert "sk-live-abc123def456" not in line
    assert "hunter2secret" not in line  # the error message is a logged string field too
    assert "[REDACTED]" in line
    assert "API_KEY" in line


def test_benign_key_values_and_prose_are_not_redacted(tmp_path):
    log_path = tmp_path / "mcp-structured-log.jsonl"
    code = 'fill = "red"\ntitle = "Token of appreciation"\n'
    instruction = {"code": code, "background": "#ff0000"}

    _logged_call(log_path, "run_sdk_code", instruction, lambda: {"ok": True})

    line = _last_log_line(log_path)
    assert "[REDACTED]" not in line
    event = json.loads(line)
    # Byte-for-byte preservation: no key:value secret shape, nothing to redact.
    assert event["instruction"]["code"] == code
    assert event["instruction"]["background"] == "#ff0000"


def test_redaction_coexists_with_field_truncation(tmp_path):
    log_path = tmp_path / "mcp-structured-log.jsonl"
    filler = "x" * (STRUCTURED_LOG_MAX_FIELD_CHARS + 5_000)
    code = 'API_KEY = "sk-live-abc123def456"\n' + filler

    result = _logged_call(log_path, "run_sdk_code", {"code": code}, lambda: {"ok": True})

    assert result == {"ok": True}
    line = _last_log_line(log_path)
    assert "sk-live-abc123def456" not in line  # redacted (it sits before any clamp)
    assert "[REDACTED]" in line
    assert "…[truncated" in line  # the oversized-field clamp still applies
