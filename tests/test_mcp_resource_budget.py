#!/usr/bin/env python3
"""Regression tests: session resources are transport-budgeted, never token bombs.

A ~124KB PDF base64-blobbed into ``get_session_resource`` once produced a
165K-char tool result that the *client's* token cap rejected outright — all of
the transfer cost, none of the payload. These tests pin the replacement
contract:

  * binary artifacts return by REFERENCE (path + bytes + sha256) by default;
  * blobs are opt-in (``mode="blob"``) and hard-capped by the result budget;
  * text artifacts paginate (``offset``/``max_chars``) and report totals;
  * JSON artifacts answer targeted JSON-pointer ``query`` requests;
  * the shared tool envelope refuses any oversized result with an actionable
    summary instead of shipping it;
  * resource endpoints raise actionable errors instead of unbounded payloads;
  * internal image loading stays uncapped (it never crosses the transport).
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
import sys

import pytest

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
_shadow = sys.modules.get("frameforge")
if _shadow is not None and not hasattr(_shadow, "__path__"):
    del sys.modules["frameforge"]
sys.path[:0] = [ROOT, os.path.join(ROOT, "src"), os.path.join(ROOT, "docs")]

from frameforge.mcp.server import _enveloped  # noqa: E402
from frameforge.mcp.sessions import (  # noqa: E402
    read_session_resource,
    session_resource_bytes,
    session_resource_endpoint_bytes,
    session_resource_endpoint_text,
)


# --------------------------------------------------------------------------- #
# Fixtures: fabricate a session directory with artifacts on disk.
# --------------------------------------------------------------------------- #
def _session(tmp_path, sid="s", **files):
    """Write ``files`` (name -> str|bytes) into a session dir; return the root."""
    session_dir = tmp_path / sid
    session_dir.mkdir(parents=True, exist_ok=True)
    for name, payload in files.items():
        path = session_dir / name
        if isinstance(payload, bytes):
            path.write_bytes(payload)
        else:
            path.write_text(payload, encoding="utf-8")
    return tmp_path


PNG_URI = "frameforge://session/s/page/1.png"
PDF_URI = "frameforge://session/s/document.pdf"
YAML_URI = "frameforge://session/s/document.yaml"
DIAG_URI = "frameforge://session/s/diagnostics.json"


# --------------------------------------------------------------------------- #
# Binary artifacts: reference by default, capped blob on request.
# --------------------------------------------------------------------------- #
def test_binary_defaults_to_reference_metadata(tmp_path):
    payload = b"\x89PNG-not-really" * 100
    root = _session(tmp_path, **{"p001.png": payload})

    result = read_session_resource(PNG_URI, session_root=root)

    assert result["mimeType"] == "image/png"
    assert "blob" not in result, "binaries must ship by reference by default"
    assert result["kind"] == "binary"
    assert result["bytes"] == len(payload)
    assert result["sha256"] == hashlib.sha256(payload).hexdigest()
    assert result["path"].endswith("p001.png")
    assert "hint" in result and "mode" in result["hint"]


def test_binary_blob_mode_roundtrips_small_file(tmp_path):
    payload = b"%PDF-1.7 tiny"
    root = _session(tmp_path, **{"document.pdf": payload})

    result = read_session_resource(PDF_URI, session_root=root, mode="blob")

    assert base64.b64decode(result["blob"]) == payload
    assert result["bytes"] == len(payload)
    assert result["sha256"] == hashlib.sha256(payload).hexdigest()
    assert result["path"].endswith("document.pdf")


def test_binary_blob_mode_refuses_over_cap(tmp_path, monkeypatch):
    monkeypatch.setenv("FRAMEFORGE_MCP_MAX_RESULT_CHARS", "4000")
    payload = os.urandom(10_000)
    root = _session(tmp_path, **{"document.pdf": payload})

    with pytest.raises(ValueError) as excinfo:
        read_session_resource(PDF_URI, session_root=root, mode="blob")
    message = str(excinfo.value)
    assert "10000" in message or "10,000" in message
    assert "FRAMEFORGE_MCP_MAX_RESULT_CHARS" in message
    assert "document.pdf" in message, "the refusal must name the on-disk path"


def test_unknown_mode_rejected(tmp_path):
    root = _session(tmp_path, **{"document.pdf": b"%PDF"})
    with pytest.raises(ValueError, match="mode"):
        read_session_resource(PDF_URI, session_root=root, mode="banana")


def test_blob_mode_rejected_for_text(tmp_path):
    root = _session(tmp_path, **{"generated.fg.yaml": "doc: {}\n"})
    with pytest.raises(ValueError, match="text artifact"):
        read_session_resource(YAML_URI, session_root=root, mode="blob")


# --------------------------------------------------------------------------- #
# Text artifacts: pagination.
# --------------------------------------------------------------------------- #
def test_text_complete_slice_reports_metadata(tmp_path):
    text = "doc:\n  title: small\n"
    root = _session(tmp_path, **{"generated.fg.yaml": text})

    result = read_session_resource(YAML_URI, session_root=root)

    assert result["text"] == text
    assert result["total_chars"] == len(text)
    assert result["offset"] == 0
    assert result["returned_chars"] == len(text)
    assert result["truncated"] is False
    assert "next_offset" not in result
    assert result["path"].endswith("generated.fg.yaml")


def test_text_paginates_and_reassembles(tmp_path, monkeypatch):
    monkeypatch.setenv("FRAMEFORGE_MCP_MAX_TEXT_CHARS", "1000")
    text = "".join(f"line-{i:05d}\n" for i in range(320))  # ~3.5K chars
    root = _session(tmp_path, **{"generated.fg.yaml": text})

    first = read_session_resource(YAML_URI, session_root=root)
    assert first["truncated"] is True
    assert first["total_chars"] == len(text)
    assert len(first["text"]) == 1000
    assert first["next_offset"] == 1000

    pieces, offset = [], 0
    for _ in range(10):
        page = read_session_resource(YAML_URI, session_root=root, offset=offset)
        pieces.append(page["text"])
        if not page["truncated"]:
            break
        offset = page["next_offset"]
    assert "".join(pieces) == text, "pagination must reassemble the exact artifact"


def test_text_max_chars_is_honoured_and_clamped(tmp_path, monkeypatch):
    monkeypatch.setenv("FRAMEFORGE_MCP_MAX_TEXT_CHARS", "1000")
    text = "x" * 5000
    root = _session(tmp_path, **{"generated.fg.yaml": text})

    small = read_session_resource(YAML_URI, session_root=root, max_chars=100)
    assert small["returned_chars"] == 100 and small["next_offset"] == 100

    clamped = read_session_resource(YAML_URI, session_root=root, max_chars=999_999)
    assert clamped["returned_chars"] == 1000, "max_chars must clamp to the slice cap"


def test_text_offset_beyond_end_returns_empty_tail(tmp_path):
    text = "short"
    root = _session(tmp_path, **{"generated.fg.yaml": text})

    result = read_session_resource(YAML_URI, session_root=root, offset=10_000)
    assert result["text"] == ""
    assert result["truncated"] is False
    assert result["returned_chars"] == 0
    assert result["total_chars"] == len(text)


# --------------------------------------------------------------------------- #
# JSON artifacts: targeted queries (RFC 6901 JSON pointer).
# --------------------------------------------------------------------------- #
DIAG = {
    "ok": True,
    "warnings": [{"kind": "font_substitution", "requested": "Archivo"}],
    "validation": {"issues": []},
}


def test_json_pointer_query_extracts_fragment(tmp_path):
    root = _session(tmp_path, **{"diagnostics.json": json.dumps(DIAG)})

    result = read_session_resource(DIAG_URI, session_root=root, query="/warnings/0/kind")

    assert result["query"] == "/warnings/0/kind"
    assert result["value"] == "font_substitution"
    assert "text" not in result, "a query answers with the fragment, not the file"


def test_json_pointer_bad_path_lists_available_keys(tmp_path):
    root = _session(tmp_path, **{"diagnostics.json": json.dumps(DIAG)})

    with pytest.raises(ValueError) as excinfo:
        read_session_resource(DIAG_URI, session_root=root, query="/nope")
    assert "warnings" in str(excinfo.value), "the error must list the available keys"


def test_query_rejected_for_non_json(tmp_path):
    root = _session(tmp_path, **{"generated.fg.yaml": "doc: {}\n"})
    with pytest.raises(ValueError, match="JSON"):
        read_session_resource(YAML_URI, session_root=root, query="/doc")


# --------------------------------------------------------------------------- #
# The shared envelope: no tool result may exceed the transport budget.
# --------------------------------------------------------------------------- #
def test_envelope_budget_refuses_oversized_result(monkeypatch):
    monkeypatch.setenv("FRAMEFORGE_MCP_MAX_RESULT_CHARS", "2000")

    result = _enveloped("probe", lambda: {
        "ok": True,
        "session_id": "s",
        "big": "y" * 10_000,
    })

    assert result["ok"] is False
    assert result["error_type"] == "ResultBudgetExceeded"
    assert result["budget"] == 2000
    assert result["chars"] > 2000
    assert any(entry["key"] == "big" for entry in result["oversized_keys"])
    assert result["kept"]["session_id"] == "s", "small scalars must survive the refusal"
    assert "FRAMEFORGE_MCP_MAX_RESULT_CHARS" in result["hint"]


def test_envelope_budget_passes_normal_result(monkeypatch):
    monkeypatch.setenv("FRAMEFORGE_MCP_MAX_RESULT_CHARS", "2000")
    payload = {"ok": True, "value": 42}
    assert _enveloped("probe", lambda: payload) == payload


# --------------------------------------------------------------------------- #
# Resource endpoints: full reads, capped with actionable errors.
# --------------------------------------------------------------------------- #
def test_endpoint_text_returns_full_content_when_in_budget(tmp_path):
    text = "doc: {}\n"
    root = _session(tmp_path, **{"generated.fg.yaml": text})
    assert session_resource_endpoint_text(YAML_URI, session_root=root) == text


def test_endpoint_text_over_budget_raises_actionably(tmp_path, monkeypatch):
    monkeypatch.setenv("FRAMEFORGE_MCP_MAX_RESULT_CHARS", "4000")
    root = _session(tmp_path, **{"generated.fg.yaml": "x" * 50_000})

    with pytest.raises(ValueError) as excinfo:
        session_resource_endpoint_text(YAML_URI, session_root=root)
    message = str(excinfo.value)
    assert "offset" in message, "the error must point at get_session_resource pagination"
    assert "generated.fg.yaml" in message


def test_endpoint_bytes_returns_raw_bytes_when_in_budget(tmp_path):
    payload = b"\x89PNG small"
    root = _session(tmp_path, **{"p001.png": payload})
    assert session_resource_endpoint_bytes(PNG_URI, session_root=root) == payload


def test_endpoint_bytes_over_budget_raises_actionably(tmp_path, monkeypatch):
    monkeypatch.setenv("FRAMEFORGE_MCP_MAX_RESOURCE_BYTES", "1024")
    root = _session(tmp_path, **{"p001.png": os.urandom(8_000)})

    with pytest.raises(ValueError) as excinfo:
        session_resource_endpoint_bytes(PNG_URI, session_root=root)
    message = str(excinfo.value)
    assert "FRAMEFORGE_MCP_MAX_RESOURCE_BYTES" in message
    assert "p001.png" in message


# --------------------------------------------------------------------------- #
# Internal readers never cross the transport — they must stay uncapped.
# --------------------------------------------------------------------------- #
def test_internal_bytes_reader_is_uncapped(tmp_path, monkeypatch):
    monkeypatch.setenv("FRAMEFORGE_MCP_MAX_RESULT_CHARS", "1000")
    monkeypatch.setenv("FRAMEFORGE_MCP_MAX_RESOURCE_BYTES", "1024")
    payload = os.urandom(50_000)
    root = _session(tmp_path, **{"p001.png": payload})

    assert session_resource_bytes(PNG_URI, session_root=root) == payload
