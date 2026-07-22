#!/usr/bin/env python3
"""The MCP guide + server `instructions` agree with the live tool registry.

Drift-risk-map HIGH #4: `FRAMEFORGE_GUIDE` (~500 lines of prose) and the
server's `instructions` string both hand-restate tool names, env knobs, and
SDK modules; the only prior test asserted the guide text is *returned* — never
that it *agrees with* the registry. Every rename/removal/addition silently
made the prose lie to every consuming agent. Pinned here, both directions:

  * every backticked tool-shaped name in the guide's "## Server tools"
    section and in `instructions` resolves against the live registry;
  * every registered tool is mentioned in the guide (the full map) —
    `instructions` is a summary and only checked forward;
  * every `FRAMEFORGE_*` env var either prose names is actually consumed
    somewhere under src/;
  * every `frameforge.sdk.<mod>` / `frameforge.<pkg>` module either prose
    names actually imports.
"""
from __future__ import annotations

import importlib
import os
import re
import sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
_shadow = sys.modules.get("frameforge")
if _shadow is not None and not hasattr(_shadow, "__path__"):
    del sys.modules["frameforge"]
sys.path[:0] = [ROOT, os.path.join(ROOT, "src"), os.path.join(ROOT, "docs")]

import pytest  # noqa: E402

from frameforge.mcp.guide import FRAMEFORGE_GUIDE  # noqa: E402
from frameforge.mcp import server as server_mod  # noqa: E402


class FakeFastMCP:
    def __init__(self, name, **kwargs):
        self.name = name
        self.kwargs = kwargs
        self.tools = {}
        self.resources = {}
        self.prompts = {}

    def tool(self, **_kw):
        def dec(f):
            self.tools[f.__name__] = f
            return f
        return dec

    def resource(self, uri, **_kw):
        def dec(f):
            self.resources[uri] = f
            return f
        return dec

    def prompt(self, **_kw):
        def dec(f):
            self.prompts[f.__name__] = f
            return f
        return dec


@pytest.fixture(scope="module")
def registry(tmp_path_factory):
    server = server_mod.create_server(
        session_root=tmp_path_factory.mktemp("guide-sync"), fastmcp_cls=FakeFastMCP)
    return set(server.tools), str(server.kwargs.get("instructions") or "")


def _backticked(text):
    return set(re.findall(r"`([A-Za-z_][A-Za-z0-9_.:/=\-']*)`", text))


def _tool_shaped(tokens, tools):
    """Names that LOOK like tool references: snake_case words whose first
    segment matches a registered tool's first segment (run_/list_/describe_…),
    or that exactly match a registered tool. Filters out parameter names,
    model fields and file paths without hand-maintaining an allowlist."""
    prefixes = {t.split("_", 1)[0] for t in tools}
    out = set()
    for tok in tokens:
        if "." in tok or "/" in tok or "=" in tok or ":" in tok or "'" in tok:
            continue
        if tok in tools:
            out.add(tok)
        elif "_" in tok and tok.split("_", 1)[0] in prefixes and tok.islower():
            out.add(tok)
    return out


# --- forward: prose names resolve --------------------------------------- #
def test_guide_server_tools_section_names_resolve(registry):
    tools, _ = registry
    m = re.search(r"## Server tools.*?(?=\n## )", FRAMEFORGE_GUIDE, re.S)
    assert m, "guide '## Server tools' section moved — update this test"
    candidates = _tool_shaped(_backticked(m.group(0)), tools)
    dead = candidates - tools
    # tool-shaped names in the tools section that are NOT tools must be a
    # deliberate, named exception — parameters documented inline.
    known_params = {"old_string", "new_string", "allow_partial", "real_metrics",
                    "session_id", "fill_mode", "stroke_style", "arrow_start",
                    "arrow_end", "label_box", "route_kind", "next_offset",
                    "total_chars", "max_chars"}
    dead -= known_params
    assert not dead, (
        f"guide '## Server tools' section names tool(s) {sorted(dead)} that the "
        "server does not register — rename or remove them (or add a genuinely "
        "new parameter name to known_params)")


def test_instructions_tool_names_resolve(registry):
    tools, instructions = registry
    assert instructions, "server instructions string is empty"
    words = set(re.findall(r"\b([a-z][a-z0-9]*(?:_[a-z0-9]+)+)\b", instructions))
    prefixes = {t.split("_", 1)[0] for t in tools}
    tool_shaped = {w for w in words if w.split("_", 1)[0] in prefixes}
    known_non_tools = {"run_in", "lower_embedded_svg", "list_fonts"}  # sdk fn + real tools ok
    dead = {w for w in tool_shaped - tools
            if w not in known_non_tools and not hasattr(
                importlib.import_module("frameforge.sdk"), w)}
    assert not dead, (
        f"server instructions name tool(s) {sorted(dead)} that are neither "
        "registered tools nor SDK exports")


# --- inverse: every tool is documented in the guide ------------------------ #
def test_every_registered_tool_is_mentioned_in_guide(registry):
    tools, _ = registry
    missing = {t for t in tools if f"`{t}`" not in FRAMEFORGE_GUIDE
               and f"`{t} " not in FRAMEFORGE_GUIDE
               and f"/ `{t}`" not in FRAMEFORGE_GUIDE
               and t not in FRAMEFORGE_GUIDE}
    assert not missing, (
        f"registered tool(s) {sorted(missing)} are absent from the guide — "
        "an MCP client reading get_guide cannot discover them")


# --- env vars + sdk modules the prose names actually exist ----------------- #
def _consumed_env_vars():
    out = set()
    for base, _dirs, files in os.walk(os.path.join(ROOT, "src")):
        for fn in files:
            if fn.endswith(".py"):
                with open(os.path.join(base, fn), encoding="utf-8") as fh:
                    out |= set(re.findall(r"FRAMEFORGE_[A-Z_]+", fh.read()))
    return out


def test_guide_and_instructions_env_vars_are_consumed(registry):
    _, instructions = registry
    named = set(re.findall(r"FRAMEFORGE_[A-Z_]+", FRAMEFORGE_GUIDE + instructions))
    consumed = _consumed_env_vars()
    ghosts = {n for n in named if n not in consumed}
    assert not ghosts, (
        f"guide/instructions name env var(s) {sorted(ghosts)} that no code "
        "under src/ reads — stale knob documentation")


def test_guide_module_mentions_import(registry):
    _, instructions = registry
    mods = set(re.findall(r"`(frameforge(?:\.[a-z_0-9]+)+)", FRAMEFORGE_GUIDE + instructions))
    bad = []
    for mod in sorted(mods):
        try:
            importlib.import_module(mod)
        except ImportError:
            # `frameforge.sdk.foo` prose may name an attribute path, not a module
            parent, _, leaf = mod.rpartition(".")
            try:
                if not hasattr(importlib.import_module(parent), leaf):
                    bad.append(mod)
            except ImportError:
                bad.append(mod)
    assert not bad, f"guide/instructions name module(s) {bad} that do not import"
