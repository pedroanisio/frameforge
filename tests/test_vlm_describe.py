#!/usr/bin/env python3
"""Local VLM describer + the describe_render MCP tool (advisory visual QA).

The VLM backend (torch/transformers/SmolVLM) is heavy and optional, so these
tests inject a fake describer — the tool's image-resolution, prompt-building
(free-form + coach stage rubric), advisory framing, and graceful degradation
(vlm group absent / bad image) are what's under test, not the model.
"""
from __future__ import annotations

import os
import sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
_shadow = sys.modules.get("framegraph")
if _shadow is not None and not hasattr(_shadow, "__path__"):
    del sys.modules["framegraph"]
sys.path[:0] = [ROOT, os.path.join(ROOT, "src")]

from framegraph.vision import vlm  # noqa: E402
from framegraph.mcp.usecases import describe_render  # noqa: E402


def _fake_vlm(monkeypatch):
    monkeypatch.setattr(vlm, "available", lambda: True)
    monkeypatch.setattr(vlm, "describe_image",
                        lambda image, prompt, **kw: f"ANSWER<{prompt[:24]}>")


def test_describe_image_raises_clear_hint_when_group_absent(monkeypatch):
    monkeypatch.setattr(vlm, "available", lambda: False)
    import pytest
    with pytest.raises(RuntimeError) as exc:
        vlm.describe_image(b"x", "hi")
    assert "vlm" in str(exc.value).lower()


def test_describe_render_absent_group_is_graceful(monkeypatch, tmp_path):
    monkeypatch.setattr(vlm, "available", lambda: False)
    res = describe_render(str(tmp_path / "x.png"), session_root=tmp_path)
    assert res["ok"] is False and res["advisory"] is True
    assert "vlm" in res["error"].lower()


def test_describe_render_free_form_question(monkeypatch, tmp_path):
    _fake_vlm(monkeypatch)
    p = tmp_path / "page.png"
    p.write_bytes(b"not-really-a-png")            # bytes only read, backend is faked
    res = describe_render(str(p), question="Does the logo read?", session_root=tmp_path)
    assert res["ok"] and res["advisory"] is True
    assert res["model"] == vlm.DEFAULT_MODEL
    assert len(res["assessment"]) == 1
    assert res["assessment"][0]["question"] == "Does the logo read?"
    assert res["assessment"][0]["answer"].startswith("ANSWER<")
    # PALS's-Law framing is surfaced so the caller never mistakes it for a measurement
    assert "unverified" in res["note"].lower() and "verify" in res["note"].lower()


def test_describe_render_runs_the_coach_stage_rubric(monkeypatch, tmp_path):
    _fake_vlm(monkeypatch)
    from framegraph.coach.critique import stage_rubric
    p = tmp_path / "page.png"
    p.write_bytes(b"x")
    res = describe_render(str(p), stage="silhouette", session_root=tmp_path)
    assert res["ok"] and res["stage"] == "silhouette"
    assert len(res["assessment"]) == len(stage_rubric("silhouette"))
    asked = [a["question"] for a in res["assessment"]]
    assert asked == stage_rubric("silhouette")


def test_describe_render_default_prompt_when_nothing_asked(monkeypatch, tmp_path):
    _fake_vlm(monkeypatch)
    p = tmp_path / "page.png"
    p.write_bytes(b"x")
    res = describe_render(str(p), session_root=tmp_path)
    assert res["ok"] and len(res["assessment"]) == 1
    assert "recognizable" in res["assessment"][0]["question"].lower()


def test_describe_render_missing_image_is_a_clean_error(monkeypatch, tmp_path):
    _fake_vlm(monkeypatch)
    res = describe_render(str(tmp_path / "nope.png"), session_root=tmp_path)
    assert res["ok"] is False and "error" in res
