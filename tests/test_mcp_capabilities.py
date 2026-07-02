#!/usr/bin/env python3
"""MCP `describe_capabilities` + `get_guide` — runtime discovery of the document model.

An agent authoring YAML/SDK code through the server must be able to look up the
live model surface (object types, flowables, inlines, style fields, canvas
presets, tool names) instead of guessing and iterating on validation errors.
The catalog is introspected LIVE from ``models/framegraph.py`` via the same
``framegraph.sdk.model`` mechanism the pipeline uses — never hand-maintained.
"""
from __future__ import annotations

import os
import sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
_shadow = sys.modules.get("framegraph")
if _shadow is not None and not hasattr(_shadow, "__path__"):
    del sys.modules["framegraph"]
sys.path[:0] = [ROOT, os.path.join(ROOT, "src"), os.path.join(ROOT, "docs")]

import framegraph.mcp.server as server_mod  # noqa: E402
from framegraph.mcp.server import FRAMEGRAPH_GUIDE, create_server, describe_capabilities  # noqa: E402


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


def test_capability_index_reflects_the_live_model():
    from framegraph.sdk.model import HEAD_VERSION

    result = describe_capabilities()

    assert result["ok"] is True
    assert result["version"] == HEAD_VERSION
    assert {"rect", "text", "line", "group", "table", "path"} <= set(result["object_types"])
    assert {"paragraph", "heading", "list", "table", "figure"} <= set(result["flowable_types"])
    assert {"ref", "cite", "math", "code", "footnote", "link", "span"} <= set(result["inline_kinds"])
    assert {"A4", "deck-16x9", "instagram-story"} <= set(result["canvas_presets"])
    assert {"deck", "book", "diagram"} <= set(result["profiles"])
    assert result["topics"], "the index must advertise the valid topic values"


def test_object_topic_returns_the_json_schema_subset():
    result = describe_capabilities(topic="rect")

    assert result["ok"] is True
    assert result["kind"] == "object"
    props = result["schema"]["properties"]
    assert "box" in props and "type" in props
    assert "box" in result["fields"]["required"] + result["fields"]["optional"]


def test_flowable_topic_returns_schema_and_fields():
    result = describe_capabilities(topic="paragraph")

    assert result["ok"] is True
    assert result["kind"] == "flowable"
    assert "text" in result["schema"]["properties"]


def test_style_topic_exposes_the_style_bag():
    result = describe_capabilities(topic="style")

    assert result["ok"] is True
    props = result["schema"]["properties"]
    assert "font_family" in props and "font_size" in props and "color" in props


def test_flowables_topic_lists_every_flow_kind_with_fields():
    result = describe_capabilities(topic="flowables")

    assert result["ok"] is True
    assert "paragraph" in result["flowables"]
    para = result["flowables"]["paragraph"]
    assert "type" in para["required"]
    assert "text" in para["optional"]


def test_inlines_topic_lists_inline_kinds():
    result = describe_capabilities(topic="inlines")

    assert result["ok"] is True
    assert {"ref", "link", "span"} <= set(result["inlines"])


def test_presets_topic_lists_canvas_presets_with_the_one_of_rule():
    result = describe_capabilities(topic="presets")

    assert result["ok"] is True
    assert "A4" in result["canvas_presets"]
    assert "exactly one" in result["note"]


def test_unknown_topic_returns_envelope_with_hint():
    result = describe_capabilities(topic="nonsense-topic")

    assert result["ok"] is False
    assert "nonsense-topic" in result["error"]
    assert "flowables" in result["hint"]


def test_tools_topic_reports_the_registered_tool_names(tmp_path):
    server = create_server(session_root=tmp_path, fastmcp_cls=FakeFastMCP)

    result = _structured(server.tools["describe_capabilities"](topic="tools"))

    assert result["ok"] is True
    assert {"run_sdk_code", "list_fonts", "describe_capabilities", "get_guide"} <= set(result["tools"])


def test_get_guide_tool_returns_the_prompt_text(tmp_path):
    server = create_server(session_root=tmp_path, fastmcp_cls=FakeFastMCP)

    assert "get_guide" in server.tools
    assert server.tools["get_guide"]() == FRAMEGRAPH_GUIDE


def test_new_tools_are_registered_and_exported(tmp_path):
    server = create_server(session_root=tmp_path, fastmcp_cls=FakeFastMCP)

    assert {"describe_capabilities", "list_fonts", "get_guide"} <= set(server.tools)
    # the server.__all__ gotcha (see commit 2e6f6d1): new tools must be re-exported.
    assert {"describe_capabilities", "list_fonts"} <= set(server_mod.__all__)
