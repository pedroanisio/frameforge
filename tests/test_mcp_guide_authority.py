#!/usr/bin/env python3
"""MCP guide authority header — the hand-maintained prose must declare itself.

``FRAMEFORGE_GUIDE`` is hand-maintained and therefore drifts; the guide must
open by saying so and by pointing at ``describe_capabilities`` as the
authoritative, live-introspected source that wins on any disagreement. It must
also carry the operational notes agents keep tripping over: sessions are
single-writer, the cleanup age floor (``FRAMEFORGE_MCP_MIN_CLEANUP_AGE``), and
the propose-input confinement env var (``FRAMEFORGE_MCP_INPUT_ROOTS``).
"""
from __future__ import annotations

import os
import sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
_shadow = sys.modules.get("frameforge")
if _shadow is not None and not hasattr(_shadow, "__path__"):
    del sys.modules["frameforge"]
sys.path[:0] = [ROOT, os.path.join(ROOT, "src"), os.path.join(ROOT, "docs")]

from frameforge.mcp.server import FRAMEFORGE_GUIDE  # noqa: E402

_OPENING_LINES = 40


def _opening() -> str:
    return "\n".join(FRAMEFORGE_GUIDE.splitlines()[:_OPENING_LINES])


def test_guide_opens_with_an_authority_note():
    opening = _opening()
    assert "describe_capabilities" in opening, (
        "the guide must point at describe_capabilities within its opening "
        f"{_OPENING_LINES} lines"
    )
    lowered = opening.lower()
    assert "hand-maintained" in lowered
    assert "authoritative" in lowered


def test_guide_notes_single_writer_sessions():
    assert "single-writer" in FRAMEFORGE_GUIDE.lower()


def test_guide_mentions_the_cleanup_age_floor_env_var():
    assert "FRAMEFORGE_MCP_MIN_CLEANUP_AGE" in FRAMEFORGE_GUIDE


def test_guide_mentions_input_roots_in_a_security_context():
    lines = FRAMEFORGE_GUIDE.splitlines()
    hits = [index for index, line in enumerate(lines) if "FRAMEFORGE_MCP_INPUT_ROOTS" in line]
    assert hits, "the guide must mention FRAMEFORGE_MCP_INPUT_ROOTS"
    markers = ("security", "posture", "confine", "harden")
    for index in hits:
        window = "\n".join(lines[max(0, index - 5) : index + 6]).lower()
        if any(marker in window for marker in markers):
            return
    raise AssertionError(
        "FRAMEFORGE_MCP_INPUT_ROOTS must be mentioned in a security/posture context"
    )
