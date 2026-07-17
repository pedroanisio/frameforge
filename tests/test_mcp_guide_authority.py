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


def test_guide_names_group_a_sdk_exposure_helpers():
    for needle in (
        "conic_gradient",
        "turbulence",
        "displacement_map",
        "diffuse_lighting",
        "specular_lighting",
        "mask_url",
        "mask_style",
        "PageBuilder`: `.rect` `.text` `.line` `.image` `.ellipse` `.circle`",
        ".curve",
        ".icon",
        ".dimension",
        ".arc",
        ".sector",
        ".ring",
        ".star",
        "running_header",
        "footnote_area",
        "define_counter",
    ):
        assert needle in FRAMEFORGE_GUIDE


def test_guide_states_backend_support_limits_for_style_effects():
    lowered = FRAMEFORGE_GUIDE.lower()
    for needle in ("cairosvg", "chromium", "filter", "blend", "mask", "backdrop_filter"):
        assert needle in lowered
    assert "may not honor" in lowered or "limited" in lowered


# --------------------------------------------------------------------------- #
#  G3 — guide tool claims are checked against the live registry, both ways     #
# --------------------------------------------------------------------------- #
class _RegistryFastMCP:
    """Minimal FastMCP double: records registered tool names."""

    def __init__(self, name: str, **kwargs):
        self.name, self.kwargs = name, kwargs
        self.tools, self.resources, self.prompts = {}, {}, {}

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


def _registered_tools(tmp_path):
    from frameforge.mcp.server import create_server

    server = create_server(session_root=tmp_path, fastmcp_cls=_RegistryFastMCP)
    return set(server.tools)


def test_guide_mentions_every_registered_tool(tmp_path):
    """A tool that exists but is absent from the guide is undiscoverable prose-side."""
    missing = sorted(t for t in _registered_tools(tmp_path) if t not in FRAMEFORGE_GUIDE)
    assert not missing, f"registered MCP tools the guide never mentions: {missing}"


def test_guide_server_tools_bullets_claim_only_real_tools(tmp_path):
    """The '## Server tools' section's `- `name`' bullets must not name ghosts."""
    import re

    lines = FRAMEFORGE_GUIDE.splitlines()
    try:
        start = next(i for i, ln in enumerate(lines) if ln.strip().startswith("## Server tools"))
    except StopIteration:
        raise AssertionError("the guide lost its '## Server tools' section")
    section = []
    for ln in lines[start + 1:]:
        if ln.startswith("## "):
            break
        section.append(ln)
    claimed = set()
    for ln in section:
        stripped = ln.strip()
        if not stripped.startswith("- `"):
            continue
        head = stripped.split("—")[0].split(" - ")[0]
        claimed.update(re.findall(r"`([a-z][a-z0-9_]*)`", head))
    registered = _registered_tools(tmp_path)
    ghosts = sorted(claimed - registered)
    assert not ghosts, f"guide Server-tools bullets claim non-existent tools: {ghosts}"
    assert claimed, "no tool bullets parsed — the Server tools section format changed"
