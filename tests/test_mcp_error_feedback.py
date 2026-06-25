#!/usr/bin/env python3
"""MCP failures must be actionable in one round-trip.

A non-zero build should surface its traceback inline (no second fetch of the
diagnostics resource), and a schema-invalid document should return structured
``validation.issues`` — not just a generic "exited with a non-zero status".
"""
from __future__ import annotations

import json
import os
import sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
_shadow = sys.modules.get("framegraph")
if _shadow is not None and not hasattr(_shadow, "__path__"):
    del sys.modules["framegraph"]
sys.path.insert(0, ROOT)

from framegraph.mcp.server import mcp_content_blocks, run_sdk_code  # noqa: E402


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
