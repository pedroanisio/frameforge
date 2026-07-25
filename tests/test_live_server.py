#!/usr/bin/env python3
"""Regression tests for the FrameForge live-session web UI."""
from __future__ import annotations

import os
import sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
_shadow = sys.modules.get("frameforge")
if _shadow is not None and not hasattr(_shadow, "__path__"):
    del sys.modules["frameforge"]
sys.path[:0] = [ROOT, os.path.join(ROOT, "src"), os.path.join(ROOT, "docs")]

from frameforge.live.server import LiveSessionStore, html_index  # noqa: E402


def test_live_session_prompt_runs_through_mcp_feedback_loop(tmp_path):
    store = LiveSessionStore(session_root=tmp_path)
    session = store.create_session("live-test")

    assert session["session_id"] == "live-test"
    assert session["events"][0]["type"] == "session_created"

    updated = store.run("live-test", "prompt", "Show a renderer status card", max_pages=1)

    result = updated["last_result"]
    assert result["ok"] is True
    assert result["live_mode"] == "prompt"
    assert result["validation"]["ok"] is True
    assert result["renders"][0]["web_url"] == "/api/sessions/live-test/resources/page/1.svg"
    assert "generated_sdk_code" in result
    assert "Show a renderer status card" in (tmp_path / "live-test" / "generated.fg.yaml").read_text(encoding="utf-8")
    assert "FrameForge live session" in (tmp_path / "live-test" / "page-001.svg").read_text(encoding="utf-8")
    assert [event["type"] for event in updated["events"]] == ["session_created", "run_started", "run_completed"]


def test_live_session_yaml_failure_is_reported_without_render(tmp_path):
    store = LiveSessionStore(session_root=tmp_path)
    store.create_session("bad-yaml")

    updated = store.run("bad-yaml", "yaml", "not: [valid", max_pages=1)

    result = updated["last_result"]
    assert result["ok"] is False
    assert result["live_mode"] == "yaml"
    assert result["renders"] == []
    assert result["validation"]["issues"]


def test_live_resource_urls_resolve_to_served_artifacts(tmp_path):
    store = LiveSessionStore(session_root=tmp_path)
    store.create_session("resource-live")
    updated = store.run("resource-live", "prompt", "HTTP render", max_pages=1)

    assert updated["last_result"]["renders"][0]["web_url"] == "/api/sessions/resource-live/resources/page/1.svg"

    mime, data = store.read_resource("resource-live", "page/1.svg")
    assert mime == "image/svg+xml"
    assert "FrameForge live session" in data.decode("utf-8")

    html = html_index()
    assert "/api/sessions" in html
    assert "FrameForge Live Session" in html
