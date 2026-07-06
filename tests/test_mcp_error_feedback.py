#!/usr/bin/env python3
"""MCP failures must be actionable in one round-trip.

A non-zero build should surface its traceback inline (no second fetch of the
diagnostics resource), and a schema-invalid document should return structured
``validation.issues`` — not just a generic "exited with a non-zero status".
Every registered tool must return the shared ``{ok: false, error, hint}``
envelope on an expected failure instead of raising, and ``ok: false`` must
always come with an ``error``.
"""
from __future__ import annotations

import json
import os
import sys
from types import SimpleNamespace

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
_shadow = sys.modules.get("framegraph")
if _shadow is not None and not hasattr(_shadow, "__path__"):
    del sys.modules["framegraph"]
sys.path[:0] = [ROOT, os.path.join(ROOT, "src"), os.path.join(ROOT, "docs")]

from framegraph.mcp.server import create_server, mcp_content_blocks, run_sdk_code  # noqa: E402


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


def test_runtime_error_surfaces_stderr_tail_in_the_summary(tmp_path):
    """A client that raises must put the traceback in the model-facing summary."""
    code = "raise RuntimeError('boom-marker-xyz')\n"
    result = run_sdk_code(code, session_id="boom", session_root=tmp_path, raster_png=False)

    assert result["ok"] is False
    summary = json.loads(mcp_content_blocks(result)[0]["text"])
    assert "stderr_tail" in summary
    assert "boom-marker-xyz" in summary["stderr_tail"]
    assert "RuntimeError" in summary["stderr_tail"]


def test_invalid_document_returns_structured_validation_issues(tmp_path):
    """A schema-invalid build lowers Pydantic errors into validation.issues."""
    code = (
        "from framegraph.sdk import DocumentBuilder\n"
        "doc = DocumentBuilder(title='Bad')\n"
        # coordinate_mode only accepts absolute|flow; this fails model validation
        "doc.page('p', canvas={'size': [100, 100], 'units': 'px'}, coordinate_mode='diagonal')\n"
    )
    result = run_sdk_code(code, session_id="bad", session_root=tmp_path, raster_png=False)

    assert result["ok"] is False
    assert result["validation"]["ok"] is False
    issues = result["validation"]["issues"]
    assert issues, "expected structured validation issues, got none"
    blob = json.dumps(issues)
    assert "coordinate_mode" in blob
    assert any(i.get("severity") == "error" for i in issues)


def test_successful_build_writes_no_build_error_sidecar(tmp_path):
    """The structured-error path is additive: a clean build leaves no sidecar."""
    code = (
        "from framegraph.sdk import DocumentBuilder\n"
        "doc = DocumentBuilder(title='Good')\n"
        "page = doc.page('p', canvas={'size': [120, 80], 'units': 'px'})\n"
        "page.layer('main').rect([0, 0, 120, 80], fill='#ffffff')\n"
    )
    result = run_sdk_code(code, session_id="good", session_root=tmp_path, raster_png=False)

    assert result["ok"] is True
    assert result["validation"]["ok"] is True
    assert not (tmp_path / "good" / "build_error.json").exists()


# --- uniform tool error envelope: expected failures never raise out of a tool ---


def test_read_sdk_client_tool_missing_file_returns_envelope_with_hint(tmp_path):
    server = create_server(session_root=tmp_path, repo_root=tmp_path, fastmcp_cls=FakeFastMCP)

    result = _structured(server.tools["read_sdk_client"]("static/examples/missing.py"))

    assert result["ok"] is False
    assert result["error_type"] == "FileNotFoundError"
    assert "list_sdk_clients" in result["hint"]


def test_write_sdk_client_tool_outside_roots_returns_envelope_with_hint(tmp_path):
    server = create_server(session_root=tmp_path, repo_root=tmp_path, fastmcp_cls=FakeFastMCP)

    result = _structured(
        server.tools["write_sdk_client"]("secrets/evil.py", "print('x')\n", create=True)
    )

    assert result["ok"] is False
    assert "allowed SDK client roots" in result["error"]
    assert "allowed_roots" in result["hint"]


def test_write_sdk_client_tool_syntax_error_returns_envelope(tmp_path):
    (tmp_path / "examples").mkdir()
    server = create_server(session_root=tmp_path, repo_root=tmp_path, fastmcp_cls=FakeFastMCP)

    result = _structured(
        server.tools["write_sdk_client"]("static/examples/broken.py", "def broken(:\n", create=True)
    )

    assert result["ok"] is False
    assert result["error_type"] == "SyntaxError"
    assert not (tmp_path / "examples" / "broken.py").exists()


def test_get_session_resource_tool_missing_artifact_returns_envelope(tmp_path):
    server = create_server(session_root=tmp_path, fastmcp_cls=FakeFastMCP)
    ok = _structured(
        server.tools["run_sdk_code"](
            "from framegraph.sdk import DocumentBuilder\n"
            "doc = DocumentBuilder(title='R')\n"
            "page = doc.page('p', canvas={'size': [100, 80], 'units': 'px'})\n"
            "page.layer('m').rect([0, 0, 100, 80], fill='#fff')\n",
            session_id="arts",
            raster_png=False,
        )
    )
    assert ok["ok"] is True

    result = _structured(
        server.tools["get_session_resource"]("framegraph://session/arts/page/9.png")
    )

    assert result["ok"] is False
    assert result["error_type"] == "FileNotFoundError"
    # the message names what IS there, so the next call needs no guessing
    assert "page-001.svg" in result["error"]
    assert "list_sessions" in result["hint"]


def test_run_sdk_code_tool_bad_session_id_returns_envelope(tmp_path):
    server = create_server(session_root=tmp_path, fastmcp_cls=FakeFastMCP)

    result = _structured(server.tools["run_sdk_code"]("print('x')", session_id="../escape"))

    assert result["ok"] is False
    assert "session_id" in result["error"]
    assert "A-Za-z0-9" in result["hint"]


# --- ok:false must always carry an error (no warning-only failures) ---


def test_pages_selector_matching_nothing_populates_error(tmp_path):
    code = (
        "from framegraph.sdk import DocumentBuilder\n"
        "doc = DocumentBuilder(title='One')\n"
        "page = doc.page('p', canvas={'size': [100, 80], 'units': 'px'})\n"
        "page.layer('m').rect([0, 0, 100, 80], fill='#fff')\n"
    )
    result = run_sdk_code(code, session_id="nopages", session_root=tmp_path,
                          pages="9", raster_png=False)

    assert result["ok"] is False
    assert "no pages matched" in result["error"]


def test_static_validation_failure_populates_error_and_hint(tmp_path, monkeypatch):
    import framegraph.mcp.pipeline as pipeline

    failing_report = SimpleNamespace(
        ok=False,
        issues=[SimpleNamespace(rule_id="R999", severity="error", path="/pages/0",
                                message="synthetic rule failure")],
    )
    monkeypatch.setattr(pipeline, "validate_static_rules", lambda _doc: failing_report)

    code = (
        "from framegraph.sdk import DocumentBuilder\n"
        "doc = DocumentBuilder(title='V')\n"
        "page = doc.page('p', canvas={'size': [100, 80], 'units': 'px'})\n"
        "page.layer('m').rect([0, 0, 100, 80], fill='#fff')\n"
    )
    result = run_sdk_code(code, session_id="valfail", session_root=tmp_path, raster_png=False)

    assert result["ok"] is False
    assert result["validation"]["ok"] is False
    assert "validation" in result["error"]
    assert "validation.issues" in result["hint"]
