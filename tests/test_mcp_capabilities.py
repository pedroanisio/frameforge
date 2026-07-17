#!/usr/bin/env python3
"""MCP `describe_capabilities` + `get_guide` — runtime discovery of the document model.

An agent authoring YAML/SDK code through the server must be able to look up the
live model surface (object types, flowables, inlines, style fields, canvas
presets, tool names) instead of guessing and iterating on validation errors.
The catalog is introspected LIVE from ``models/frameforge.py`` via the same
``frameforge.sdk.model`` mechanism the pipeline uses — never hand-maintained.
"""
from __future__ import annotations

import os
import sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
_shadow = sys.modules.get("frameforge")
if _shadow is not None and not hasattr(_shadow, "__path__"):
    del sys.modules["frameforge"]
sys.path[:0] = [ROOT, os.path.join(ROOT, "src"), os.path.join(ROOT, "docs")]

import frameforge.mcp.server as server_mod  # noqa: E402
from frameforge.mcp.server import FRAMEFORGE_GUIDE, create_server, describe_capabilities  # noqa: E402


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
    from frameforge.sdk.model import HEAD_VERSION

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
    assert server.tools["get_guide"]() == FRAMEFORGE_GUIDE


def test_new_tools_are_registered_and_exported(tmp_path):
    server = create_server(session_root=tmp_path, fastmcp_cls=FakeFastMCP)

    assert {"describe_capabilities", "list_fonts", "get_guide"} <= set(server.tools)
    # the server.__all__ gotcha (see commit 2e6f6d1): new tools must be re-exported.
    assert {"describe_capabilities", "list_fonts"} <= set(server_mod.__all__)


# ── guide coverage drift-gate (MCP round, 2026-07-03) ──────────────────────
# The guide is the model-facing capability map: a delivered SDK surface that
# never reaches it is invisible to every MCP client. Two gates:
#   1. every capability-bearing sdk module is mentioned by name;
#   2. the headline callables/fields of the recent delivery waves appear.
# When either fails for NEW work, extend the guide — not this list's spirit.

_CAPABILITY_MODULES = [
    # capability-bearing sdk modules — each MUST be named in the guide.
    "book", "canon", "chart", "chevreul", "clip", "draw", "expand", "fields",
    "figure", "flow", "fractal", "geometry", "humanize", "lattices", "layout",
    "macros", "manifold", "markdown", "metrics", "outline", "paint", "planar",
    "recolor", "region", "topology", "widgets",
]

# Internal plumbing that carries no author-facing capability of its own — the
# only sdk modules allowed to be absent from both the guide and the list above.
_PLUMBING_EXEMPT = {"author", "conform", "io", "model", "validate"}

_HEADLINE_SURFACES = [
    # W1 planar kernel (#45)
    "union", "offset_polygon", "split_at", "cut_along", "fill_regions",
    # W2 stroke outlines + kerning (#46)
    "stroke_outline", "repeat_along_path", "kerned_spans", "font_kern_pairs",
    # W4 style richness (#48)
    "effects:", "appearance:", "recolor(", "color_guide",
    "fill_styles",
    # CG-canon geometry (B-backlog residuals: patches, curvature, 3D hull, near-clip)
    "bspline_patch", "surface_curvature", "convex_hull_3d", "near_clip",
    # absorption programme (#28/#29/#31/#32/#33)
    "frameforge.patterns", "load_catalog", "compose(",
    "frameforge.library", "load_theme", "load_symbols",
    "honeycomb_capability_map", "module_hub_radial",
    "from_markdown", "--from-v01",
    # cross-cutting
    "expand(", "humanize", "measure_text",
]


def test_guide_mentions_every_capability_bearing_sdk_module():
    from pathlib import Path
    sdk_dir = Path(__file__).resolve().parent.parent / "src" / "frameforge" / "sdk"
    live = {p.stem for p in sdk_dir.glob("*.py") if not p.stem.startswith("_")}
    missing_from_tree = set(_CAPABILITY_MODULES) - live
    assert not missing_from_tree, f"gate list names dead modules: {missing_from_tree}"
    # Bidirectional: every LIVE module is either a declared capability module or
    # explicitly exempt plumbing — so a NEW module can never slip through
    # unclassified and silently escape the guide-coverage gate below.
    unclassified = live - set(_CAPABILITY_MODULES) - _PLUMBING_EXEMPT
    assert not unclassified, (
        "new sdk modules are neither declared capabilities nor exempt plumbing "
        f"(classify them): {sorted(unclassified)}")
    unmentioned = [m for m in _CAPABILITY_MODULES if m not in FRAMEFORGE_GUIDE]
    assert not unmentioned, (
        f"sdk modules invisible to MCP clients (extend the guide): {unmentioned}")


def test_guide_covers_the_delivered_headline_surfaces():
    missing = [s for s in _HEADLINE_SURFACES if s not in FRAMEFORGE_GUIDE]
    assert not missing, f"delivered surfaces missing from the guide: {missing}"


def test_color_guide_is_a_top_level_sdk_export():
    # `chevreul.color_guide` is advertised in the guide, the headline gate above,
    # and the server handshake — it must be a top-level `frameforge.sdk` export so
    # the introspected capability manifest (built from sdk.__all__) can see it.
    import frameforge.sdk as sdk
    assert "color_guide" in sdk.__all__, "color_guide missing from frameforge.sdk.__all__"
    assert hasattr(sdk, "color_guide"), "color_guide not re-exported from frameforge.sdk"


def test_server_instructions_name_the_authoring_engines(tmp_path):
    server = create_server(session_root=tmp_path, fastmcp_cls=FakeFastMCP)
    text = server.kwargs["instructions"]
    for surface in ("sdk.planar", "sdk.outline", "frameforge.patterns",
                    "frameforge.library", "--from-v01"):
        assert surface in text, f"handshake instructions omit {surface}"
