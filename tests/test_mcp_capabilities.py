#!/usr/bin/env python3
"""MCP `describe_capabilities` + `get_guide` — runtime discovery of the document model.

An agent authoring YAML/SDK code through the server must be able to look up the
live model surface (object types, flowables, inlines, style fields, canvas
presets, tool names) instead of guessing and iterating on validation errors.
The catalog is introspected LIVE from ``models/frameforge.py`` via the same
``frameforge_sdk.model`` mechanism the pipeline uses — never hand-maintained.
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
    from frameforge_sdk.model import HEAD_VERSION

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
    props = result["properties"]          # own fields, promoted out of the $defs dump
    assert "box" in props and "type" in props
    assert "schema" not in result         # no full recursive $defs graph inline
    assert "box" in result["fields"]["required"] + result["fields"]["optional"]


def test_flowable_topic_returns_schema_and_fields():
    result = describe_capabilities(topic="paragraph")

    assert result["ok"] is True
    assert result["kind"] == "flowable"
    assert "text" in result["properties"]
    assert "references" in result         # nested types are listed for drill-down


def test_style_topic_exposes_the_style_bag():
    result = describe_capabilities(topic="style")

    assert result["ok"] is True
    props = result["properties"]
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
    assert {"run_sdk_code", "list_fonts", "fit_text", "describe_capabilities", "get_guide"} <= set(result["tools"])


def test_get_guide_tool_returns_the_prompt_text(tmp_path):
    server = create_server(session_root=tmp_path, fastmcp_cls=FakeFastMCP)

    assert "get_guide" in server.tools
    assert server.tools["get_guide"]() == FRAMEFORGE_GUIDE


def test_new_tools_are_registered_and_exported(tmp_path):
    server = create_server(session_root=tmp_path, fastmcp_cls=FakeFastMCP)

    assert {"describe_capabilities", "list_fonts", "fit_text", "get_guide"} <= set(server.tools)
    # the server.__all__ gotcha (see commit 2e6f6d1): new tools must be re-exported.
    assert {"describe_capabilities", "list_fonts", "fit_text"} <= set(server_mod.__all__)

    import frameforge.mcp as mcp
    assert "fit_text" in mcp.__all__
    assert callable(mcp.fit_text)


# ── guide coverage drift-gate (MCP round, 2026-07-03) ──────────────────────
# The guide is the model-facing capability map: a delivered SDK surface that
# never reaches it is invisible to every MCP client. Two gates:
#   1. every capability-bearing sdk module is mentioned by name;
#   2. the headline callables/fields of the recent delivery waves appear.
# When either fails for NEW work, extend the guide — not this list's spirit.

_CAPABILITY_MODULES = [
    # capability-bearing sdk modules — each MUST be named in the guide.
    "book", "canon", "chart", "chevreul", "clip", "colorspace", "draw", "expand", "fields",
    "figure", "flow", "fractal", "geometry", "humanize", "lattices", "layout",
    "macros", "manifold", "markdown", "metrics", "noise", "outline", "paint", "params",
    "pathtext", "planar", "rand", "recolor", "region", "separate", "solids", "topology",
    "sugiyama", "uml_models", "widgets",
]

# Internal plumbing that carries no author-facing capability of its own — the
# only sdk modules allowed to be absent from both the guide and the list above.
_PLUMBING_EXEMPT = {"author", "conform", "io", "model", "provenance", "validate"}

_HEADLINE_SURFACES = [
    # SDK discovery residuals (#57)
    "FlowBuilder", "grid(", "inset(",
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
    # UML 2.5.1 absorption (#30)
    "sugiyama_layout", "UMLClassDiagramModel", "compose_class_diagram",
    "compose_sequence_diagram", "compose_state_machine", "to_document",
    # cross-cutting
    "expand(", "humanize", "measure_text", "fit_width",
    # deterministic generative substrate (#90)
    "Rand", "halton", "poisson_disk", "jittered_grid",
    # sampleable coherent noise (#91)
    "Noise", "value_noise_2d", "perlin_2d", "simplex_2d", "fbm", "domain_warp",
    # perceptual colour core (#92)
    "to_oklab", "from_oklab", "mix(", "ramp(", "delta_e",
]


def test_guide_explains_deterministic_sampling_workflow():
    required_fragments = (
        "frameforge_sdk.rand",
        "from frameforge_sdk import Rand, halton, poisson_disk, jittered_grid",
        "independent named sub-stream",
        "page space is Y-down",
        "not cryptographic",
        "run_sdk_code",
    )

    missing = [fragment for fragment in required_fragments if fragment not in FRAMEFORGE_GUIDE]
    assert not missing, f"MCP guide omits deterministic sampling guidance: {missing}"


def test_sdk_discovery_exposes_deterministic_sampling_contracts():
    result = describe_capabilities(topic="sdk")
    summaries = {item["name"]: item["summary"] for item in result["exports"]}

    assert "deterministic" in summaries["Rand"].lower()
    assert "low-discrepancy" in summaries["halton"].lower()
    assert "minimum separation" in summaries["poisson_disk"].lower()
    assert "one point per cell" in summaries["jittered_grid"].lower()


def test_guide_explains_sampleable_noise_and_filter_distinction():
    required_fragments = (
        "frameforge_sdk.noise",
        "from frameforge_sdk import Noise, ScalarField, domain_warp",
        "ScalarField(Noise(7, basis=\"simplex\").field()",
        "author-time CPU values",
        "paint.turbulence",
        "renderer-side",
        "not cryptographic",
        "run_sdk_code",
    )
    missing = [fragment for fragment in required_fragments if fragment not in FRAMEFORGE_GUIDE]
    assert not missing, f"MCP guide omits sampleable-noise guidance: {missing}"


def test_sdk_discovery_exposes_sampleable_noise_contracts():
    result = describe_capabilities(topic="sdk")
    summaries = {item["name"]: item["summary"] for item in result["exports"]}

    assert "seed" in summaries["Noise"].lower()
    assert "[0, 1]" in summaries["value_noise_2d"]
    assert "perlin" in summaries["perlin_2d"].lower()
    assert "simplex" in summaries["simplex_2d"].lower()
    assert "brownian" in summaries["fbm"].lower()
    assert "warped" in summaries["domain_warp"].lower()


def test_guide_explains_perceptual_color_workflow_and_legacy_default():
    required_fragments = (
        "frameforge_sdk.colorspace",
        "from frameforge_sdk import delta_e, mix, ramp, to_oklab",
        "mix(\"#172a46\", \"#f3c969\", 0.5, space=\"oklab\")",
        "new `mix` and `ramp` default to OKLab",
        "Chevreul helpers keep `space=\"srgb\"`",
        "clips out-of-gamut",
        "run_sdk_code",
    )
    missing = [fragment for fragment in required_fragments if fragment not in FRAMEFORGE_GUIDE]
    assert not missing, f"MCP guide omits perceptual-colour guidance: {missing}"


def test_sdk_discovery_exposes_perceptual_color_contracts():
    result = describe_capabilities(topic="sdk")
    summaries = {item["name"]: item["summary"] for item in result["exports"]}

    assert "oklab" in summaries["mix"].lower()
    assert "evenly" in summaries["ramp"].lower()
    assert "perceptual distance" in summaries["delta_e"].lower()
    assert "d65" in summaries["to_lab"].lower()


def test_guide_documents_pdf_tex_object_effect_coverage_and_approximations():
    guide = " ".join(FRAMEFORGE_GUIDE.split())
    assert "pdf-tex" in guide
    assert "line, polyline, polygon, path, curve/bezier, text, image, and table" in guide
    assert "translated translucent silhouette" in guide
    assert "eight fixed neighbouring silhouettes" in guide
    assert "bounding-box silhouette" in guide


def test_guide_mentions_every_capability_bearing_sdk_module():
    from pathlib import Path

    # The SDK is the standalone `frameforge-sdk` distribution since 2026-08-01,
    # so its modules are no longer a path inside this repo. Resolve through the
    # import system: this follows an editable checkout, a git pin or a wheel.
    import frameforge_sdk
    sdk_dir = Path(frameforge_sdk.__file__).resolve().parent
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


def test_guide_explains_standalone_flow_and_static_layout_entry_points():
    required_fragments = (
        "from frameforge_sdk import FlowBuilder, grid, inset",
        "FlowBuilder().heading",
        ".story()",
        'doc.flow("report", master=body_master, story=story)',
        "inset([0, 0, 1280, 720], [48, 64])",
        "grid(content, cols=3, count=5, gap=24)",
        "[x, y, w, h]",
    )

    missing = [fragment for fragment in required_fragments if fragment not in FRAMEFORGE_GUIDE]
    assert not missing, f"MCP guide omits executable SDK discovery guidance: {missing}"


def test_get_guide_delivers_live_top_level_flow_and_layout_exports(tmp_path):
    import frameforge_sdk as sdk

    for name in ("FlowBuilder", "grid", "inset"):
        assert name in sdk.__all__
        assert callable(getattr(sdk, name))

    server = create_server(session_root=tmp_path, fastmcp_cls=FakeFastMCP)
    guide = server.tools["get_guide"]()
    assert "from frameforge_sdk import FlowBuilder, grid, inset" in guide
    assert "DocumentBuilder.flow" in guide
    assert "pure functions returning static `[x, y, w, h]`" in guide


def test_guide_explains_noise_filter_preset_contracts():
    required_fragments = (
        "`displacement_map(...)` is self-noised",
        "`base_frequency`, `num_octaves`, `seed`, and noise `type`",
        "do not prepend a",
        "`turbulence(...)` item",
        "strength is `opacity`",
        "blend operation is `mode`",
    )

    missing = [fragment for fragment in required_fragments if fragment not in FRAMEFORGE_GUIDE]
    assert not missing, f"MCP guide omits noise-filter preset semantics: {missing}"


def test_sdk_discovery_summarizes_noise_filter_preset_contracts():
    result = describe_capabilities(topic="sdk")
    summaries = {item["name"]: item["summary"] for item in result["exports"]}

    assert "self-noised" in summaries["displacement_map"]
    assert "blend-texture" in summaries["turbulence"]


def test_color_guide_is_a_top_level_sdk_export():
    # `chevreul.color_guide` is advertised in the guide, the headline gate above,
    # and the server handshake — it must be a top-level `frameforge_sdk` export so
    # the introspected capability manifest (built from sdk.__all__) can see it.
    import frameforge_sdk as sdk
    assert "color_guide" in sdk.__all__, "color_guide missing from frameforge_sdk.__all__"
    assert hasattr(sdk, "color_guide"), "color_guide not re-exported from frameforge_sdk"


def test_server_instructions_name_the_authoring_engines(tmp_path):
    server = create_server(session_root=tmp_path, fastmcp_cls=FakeFastMCP)
    text = server.kwargs["instructions"]
    for surface in ("sdk.planar", "sdk.outline", "frameforge.patterns",
                    "frameforge.library", "--from-v01"):
        assert surface in text, f"handshake instructions omit {surface}"


# --- output-size resilience: no topic may blow the MCP result ceiling --------
#     Regression for describe_capabilities returning 70KB-280KB schema dumps
#     (the whole recursive $defs graph inline). Progressive disclosure: a schema
#     topic returns its OWN properties + a `references` list of nested types to
#     drill into, never the full graph.

import json  # noqa: E402

from frameforge.mcp.config import max_result_chars  # noqa: E402
from frameforge.mcp.discovery import _CAPABILITY_TOPICS, _model_catalog  # noqa: E402

CAP_BUDGET = 40_000  # chars; well under the observed ~65KB per-result ceiling

# The `sdk` topic is the one flat, complete index on the surface: a sibling gate
# (test_sdk_topic_matches_package_all_exactly) REQUIRES it to name every entry in
# frameforge_sdk.__all__, so its size is O(exports) and grows with each new SDK
# feature. Completeness and a fixed char budget are in permanent tension, and
# CAP_BUDGET is a self-imposed margin, not the real limit — the transport ceiling
# is FRAMEFORGE_MCP_MAX_RESULT_CHARS, enforced at runtime in server.py (an
# over-budget result is refused outright rather than shipped). So the sdk topic is
# held to that REAL budget with a margin, while every schema topic keeps the tight
# CAP_BUDGET, because for those progressive disclosure — not completeness — is the
# design statement, and 40k is what states it.
SDK_TOPIC_BUDGET = max_result_chars() - 10_000


def _budget_for(topic):
    return SDK_TOPIC_BUDGET if topic == "sdk" else CAP_BUDGET


def _all_topics():
    cat = _model_catalog()
    schema_topics = sorted(
        set(cat["objects"]) | set(cat["flowables"]) | set(cat["inlines"]) | set(cat["named"])
    )
    return [None] + list(_CAPABILITY_TOPICS) + schema_topics


def test_no_capability_topic_exceeds_the_result_budget():
    """Every describe_capabilities response stays under the MCP result ceiling.

    This is the drift guard: the model grows, and without this a new type or a
    deeper nesting silently pushes a topic past the token limit again.
    """
    over = []
    for topic in _all_topics():
        result = describe_capabilities(topic, tool_names=["a", "b"])
        size = len(json.dumps(result, default=str))
        if size > _budget_for(topic):
            over.append((topic or "<index>", size, _budget_for(topic)))
    assert not over, f"topics over their budget (progressive disclosure regressed): {over}"


def test_the_sdk_topic_still_fits_the_real_transport_budget():
    """The complete sdk index must survive the transport, not just the margin.

    server.py refuses to ship a result over FRAMEFORGE_MCP_MAX_RESULT_CHARS, so
    this is the gate that actually protects discovery from breaking in the field.
    """
    size = len(json.dumps(describe_capabilities("sdk"), default=str))
    assert size < max_result_chars(), (
        f"the sdk topic is {size} chars — server.py would refuse to ship it "
        f"(budget {max_result_chars()}); the flat complete index needs compacting"
    )


def test_object_schema_topic_is_compact_with_references():
    """A container schema returns own properties + references, not the $defs graph."""
    result = describe_capabilities("group")
    assert result["ok"] and result["kind"] == "object"
    assert result["properties"], "own properties missing"
    assert result["references"], "nested-type references missing"
    assert "schema" not in result, "full recursive schema must not be inlined"
    assert len(json.dumps(result, default=str)) < 20_000, "container topic still too large"


def test_referenced_type_is_itself_drillable():
    """Progressive disclosure: a referenced nested type resolves to its own topic."""
    result = describe_capabilities("group")
    cat = _model_catalog()
    valid = set(cat["objects"]) | set(cat["flowables"]) | set(cat["inlines"]) | set(cat["named"])
    drillable = [r for r in result["references"] if r.lower() in valid]
    assert drillable, f"no reference drills down: {result['references'][:10]}"
    child = describe_capabilities(drillable[0].lower())
    assert child["ok"] and child["properties"], f"drilling {drillable[0]} failed"


def test_leaf_topic_keeps_its_own_fields():
    """Compaction must not lose the type's own information."""
    result = describe_capabilities("rect")
    assert "box" in result["properties"] or "fill" in result["properties"]
    fields = result["fields"]
    assert fields["required"] or fields["optional"]


def test_sdk_topic_is_bounded_and_still_lists_exports():
    result = describe_capabilities("sdk")
    assert result["ok"]
    assert len(json.dumps(result, default=str)) < SDK_TOPIC_BUDGET, "sdk export list too large"
    names = [e["name"] for e in result["exports"]]
    assert "DocumentBuilder" in names


def test_style_topic_still_carries_reserved_styles():
    """The style special-case (ADR-0006 reserved styles) survives compaction."""
    result = describe_capabilities("style")
    assert result["ok"]
    assert "body" in result["reserved_styles"] and "caption" in result["reserved_styles"]
