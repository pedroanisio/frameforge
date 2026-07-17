#!/usr/bin/env python3
"""MCP `list_fonts` — font-family discovery and resolution.

Rendering resolves families via fontconfig, and an unresolved family silently
substitutes a default face; the tool lets an agent verify a family exists (and
what fontconfig actually resolves a request to) BEFORE rendering. It must
degrade to a structured error with an actionable hint when fontconfig is absent.
"""
from __future__ import annotations

import os
import shutil
import sys

import pytest

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
_shadow = sys.modules.get("frameforge")
if _shadow is not None and not hasattr(_shadow, "__path__"):
    del sys.modules["frameforge"]
sys.path[:0] = [ROOT, os.path.join(ROOT, "src"), os.path.join(ROOT, "docs")]

import frameforge.mcp.discovery as discovery  # noqa: E402
from frameforge.mcp.server import list_fonts  # noqa: E402


def _fake_fc(outputs: dict[str, str]):
    """Return a `_run_fc` stand-in keyed by the fc binary name."""

    def run(args):
        return outputs[args[0]]

    return run


def test_list_fonts_enumerates_unique_sorted_families(monkeypatch):
    monkeypatch.setattr(discovery, "_fc_available", lambda: True)
    monkeypatch.setattr(
        discovery, "_run_fc",
        _fake_fc({"fc-list": "DejaVu Sans\nInter,Inter Display\nDejaVu Sans\nZ Font\n"}),
    )

    result = list_fonts()

    assert result["ok"] is True
    assert result["families"] == ["DejaVu Sans", "Inter", "Inter Display", "Z Font"]
    assert result["family_count"] == 4
    assert result["truncated"] is False


def test_list_fonts_filters_and_truncates(monkeypatch):
    monkeypatch.setattr(discovery, "_fc_available", lambda: True)
    monkeypatch.setattr(
        discovery, "_run_fc",
        _fake_fc({"fc-list": "Alpha One\nAlpha Two\nBeta\n"}),
    )

    result = list_fonts(contains="alpha", limit=1)

    assert result["ok"] is True
    assert result["family_count"] == 2  # both Alphas matched the filter
    assert result["families"] == ["Alpha One"]  # but only `limit` are returned
    assert result["truncated"] is True


def test_list_fonts_resolves_a_requested_family(monkeypatch):
    monkeypatch.setattr(discovery, "_fc_available", lambda: True)
    monkeypatch.setattr(
        discovery, "_run_fc",
        _fake_fc({"fc-list": "Inter\nDejaVu Sans\n", "fc-match": "DejaVu Sans"}),
    )

    result = list_fonts(family="Inter ExtraLight")

    assert result["ok"] is True
    resolves = result["resolves"]
    assert resolves["requested"] == "Inter ExtraLight"
    assert resolves["resolved_family"] == "DejaVu Sans"
    assert resolves["exact"] is False
    assert "substitut" in resolves["note"]  # the silent-substitution warning is explicit


def test_list_fonts_exact_resolution_has_no_substitution_note(monkeypatch):
    monkeypatch.setattr(discovery, "_fc_available", lambda: True)
    monkeypatch.setattr(
        discovery, "_run_fc",
        _fake_fc({"fc-list": "Inter\n", "fc-match": "Inter"}),
    )

    result = list_fonts(family="inter")

    assert result["resolves"]["exact"] is True
    assert "note" not in result["resolves"]


def test_list_fonts_degrades_structured_when_fontconfig_absent(monkeypatch):
    monkeypatch.setattr(discovery, "_fc_available", lambda: False)

    result = list_fonts()

    assert result["ok"] is False
    assert "fontconfig" in result["error"]
    assert result["hint"], "the failure must say how to get fontconfig"
    assert result["families"] == []


def test_list_fonts_reports_pinned_session_fonts(monkeypatch, tmp_path):
    monkeypatch.setattr(discovery, "_fc_available", lambda: True)
    monkeypatch.setattr(discovery, "_run_fc", _fake_fc({"fc-list": "Arial\n"}))
    session_dir = tmp_path / "pinned"
    session_dir.mkdir()
    (session_dir / "generated.fg.yaml").write_text(
        "dsl: FrameForge\n"
        "version: 2.2.0\n"
        "defs:\n"
        "  tokens:\n"
        "    fonts:\n"
        "      display:\n"
        "        family: Big Shoulders\n"
        "      plain: Arial\n"
        "pages: []\n",
        encoding="utf-8",
    )

    result = list_fonts(session_id="pinned", session_root=tmp_path)

    assert result["ok"] is True
    assert {"name": "display", "family": "Big Shoulders"} in result["pinned_fonts"]
    assert {"name": "plain", "family": "Arial"} in result["pinned_fonts"]


def test_list_fonts_without_session_doc_has_no_pinned_fonts(monkeypatch, tmp_path):
    monkeypatch.setattr(discovery, "_fc_available", lambda: True)
    monkeypatch.setattr(discovery, "_run_fc", _fake_fc({"fc-list": "Arial\n"}))

    result = list_fonts(session_id="nodoc", session_root=tmp_path)

    assert result["ok"] is True
    assert result["pinned_fonts"] == []


@pytest.mark.skipif(shutil.which("fc-list") is None, reason="fontconfig not installed")
def test_list_fonts_against_the_real_fontconfig():
    result = list_fonts(limit=10)

    assert result["ok"] is True
    assert result["family_count"] >= 1
    assert len(result["families"]) <= 10
